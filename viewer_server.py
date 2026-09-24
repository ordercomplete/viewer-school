# -*- coding: utf-8 -*-
"""
Локальний HTTP-сервер для viewer.html.

Навіщо: сторінка, відкрита через file://, не має права запускати
зовнішні програми (пісочниця браузера). Тому запускаємо маленький
сервер на 127.0.0.1, який:
  * роздає файли папки (з підтримкою Range — щоб працювала перемотка відео);
  * за запитом GET /api/regen перезапускає generate_viewer.py
    (оновлює дерево файлів і саму сторінку viewer.html);
  * GET /api/status — перевірка «сервер живий» (використовує start_viewer.bat).

Запуск: python viewer_server.py [--port 8321] [--open]
Залежностей немає — тільки стандартна бібліотека.
"""
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
# stderr теж у UTF-8: інакше повідомлення про помилки у перенаправлених
# виводах (файл/пайп) виходять «кракозябрами» через кодову сторінку консолі.
try:
    cast(io.TextIOWrapper, sys.stderr).reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

SCRIPT_DIR = Path(__file__).resolve().parent   # тека зі скриптами додатка
OUT_NAME = "viewer.html"
GEN_SCRIPT = SCRIPT_DIR / "generate_viewer.py"
# Тека матеріалів, яку роздає сервер: типово — тека скриптів,
# змінюється аргументом --root (ярлик «Згенерувати для теки…»).
BASE = SCRIPT_DIR
DEFAULT_PORT = 8321
PORT_TRIES = 9
GEN_TIMEOUT_S = 1800                          # максимум на генерацію
HOST = "127.0.0.1"


def port_file() -> Path:
    """Файл із фактичним портом — у теці матеріалів (BASE)."""
    return BASE / "viewer_server.port"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".pdf": "application/pdf",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".gif": "image/gif",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    ".jar": "application/java-archive",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml"
             ".presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml"
             ".document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml"
             ".sheet",
}

GEN_LOCK = threading.Lock()
STATE: dict[str, Any] = {"busy": False, "last_ms": 0, "last_ok": None,
                         "last_error": "", "runs": 0}
PORT_ACTUAL = DEFAULT_PORT      # фактичний порт (заповнюється у main)


def safe_stat(path: Path) -> os.stat_result | None:
    """stat() без винятків: файл може зникнути саме під час перегенерації."""
    try:
        return path.stat()
    except OSError:
        return None


def find_running_server(start: int, tries: int = PORT_TRIES) -> int | None:
    """Шукає вже запущений viewer_server у діапазоні портів."""
    import urllib.error
    import urllib.request
    for port in range(start, start + tries):
        try:
            with urllib.request.urlopen(
                    f"http://{HOST}:{port}/api/status", timeout=1.2) as r:
                data = json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("server") == "viewer_server":
            found_root = data.get("root")
            # «свій» сервер — той, що роздає саму цю теку
            if found_root in (None, "", str(BASE)):
                return port
    return None


def port_in_use(port: int) -> bool:
    """Чи зайнятий порт (Windows-безпечна перевірка).

    Спершу пробуємо з'єднатися (ловить будь-який слухач), потім — bind
    без SO_REUSEADDR (на Windows це відрізняє «свій» сокет від чужого).
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        if probe.connect_ex((HOST, port)) == 0:
            return True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((HOST, port))
        except OSError:
            return True
    return False


def free_port(start: int, tries: int = PORT_TRIES) -> int:
    """Перший вільний порт у діапазоні start..start+tries-1."""
    for port in range(start, start + tries):
        if not port_in_use(port):
            return port
    raise SystemExit(f"ПОМИЛКА: усі порти {start}..{start + tries - 1} зайняті.")


def run_generator() -> dict[str, Any]:
    """Запускає generate_viewer.py. Повертає словник зі статусом."""
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(GEN_SCRIPT), str(BASE)],
            cwd=str(BASE), capture_output=True, timeout=GEN_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": int((time.time() - started) * 1000),
                "error": f"перевищено таймаут {GEN_TIMEOUT_S} с"}
    except OSError as e:
        return {"ok": False, "ms": int((time.time() - started) * 1000),
                "error": f"не вдалося запустити генератор: {e}"}

    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()
    page = BASE / OUT_NAME
    page_stat = safe_stat(page)
    return {
        "ok": proc.returncode == 0 and page_stat is not None,
        "ms": int((time.time() - started) * 1000),
        "code": proc.returncode,
        "output": out[-1500:],
        "stderrTail": err[-600:],
        "pageSize": page_stat.st_size if page_stat else 0,
        "pageTime": int(page_stat.st_mtime) if page_stat else 0,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "Viewer-for-School/1.1"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------- утиліти
    def _json(self, data: dict[str, Any], code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _error(self, code: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _local_path(self) -> Path | None:
        """URL → безпечний шлях усередині BASE (або None, якщо вихід за межі)."""
        rel = unquote(urlparse(self.path).path).lstrip("/")
        if not rel:
            return BASE / OUT_NAME
        try:
            real = (BASE / rel).resolve()
            real.relative_to(BASE)
        except (ValueError, OSError):
            return None
        return real

    # -------------------------------------------------------------- запити
    def do_OPTIONS(self) -> None:                       # CORS-запит від file://
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        route = urlparse(self.path).path

        if route in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/" + OUT_NAME)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if route == "/api/status":
            page = BASE / OUT_NAME
            st = safe_stat(page)
            self._json({
                "ok": True,
                "server": "viewer_server",
                "root": str(BASE),
                "port": PORT_ACTUAL,
                "pageExists": st is not None,
                "pageTime": int(st.st_mtime) if st else 0,
                "busy": STATE["busy"],
                "runs": STATE["runs"],
                "lastMs": STATE["last_ms"],
                "lastOk": STATE["last_ok"],
                "lastError": STATE["last_error"][:300],
            })
            return

        if route == "/api/regen":
            self._handle_regen()
            return

        # ---------------------------------------------------- статичні файли
        path = self._local_path()
        if path is None:
            self._error(403, "Доступ за межами папки заборонено")
            return
        if not path.is_file():
            self._error(404, f"Не знайдено: {self.path}")
            return
        self._send_file(path)

    def do_HEAD(self) -> None:
        path = self._local_path()
        if path is None or not path.is_file():
            self._error(404, "Не знайдено")
            return
        self._send_file(path, head_only=True)

    # ------------------------------------------------------------- регенерація
    def _handle_regen(self) -> None:
        if not GEN_LOCK.acquire(blocking=False):
            self._json({"ok": False, "busy": True,
                        "error": "оновлення вже виконується"}, 409)
            return
        STATE["busy"] = True
        try:
            info = run_generator()
            STATE["runs"] = int(STATE["runs"]) + 1
            STATE["last_ms"] = info.get("ms", 0)
            STATE["last_ok"] = info.get("ok")
            STATE["last_error"] = info.get("error") or info.get("stderrTail", "")
            print(f"[regen] ok={info.get('ok')} {info.get('ms')} мс", flush=True)
            self._json(info, 200 if info.get("ok") else 500)
        except Exception as e:                  # noqa: BLE001 — сервер не має падати
            STATE["last_ok"] = False
            STATE["last_error"] = str(e)
            self._json({"ok": False, "error": f"внутрішня помилка: {e}"}, 500)
        finally:
            STATE["busy"] = False
            GEN_LOCK.release()

    # ------------------------------------------------------------- віддача файлу
    def _send_file(self, path: Path, head_only: bool = False) -> None:
        try:
            size = path.stat().st_size
        except OSError:
            self._error(404, "Файл недоступний")
            return

        ctype = guess_mime(path)
        start, end = 0, size - 1
        code = 200
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                g1, g2 = m.group(1), m.group(2)
                if g1:
                    start = int(g1)
                    end = int(g2) if g2 else size - 1
                elif g2:                                # bytes=-500 → останні 500 Б
                    start = max(0, size - int(g2))
                    end = size - 1
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                code = 206

        length = max(0, end - start + 1)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if head_only:
            return

        remaining = length
        try:
            with path.open("rb") as fh:
                fh.seek(start)
                while remaining > 0:
                    chunk = fh.read(min(262144, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass                        # клієнт закрив вкладку або перемотав відео

    # -------------------------------------------------------------- логування
    def handle_one_request(self) -> None:
        """Обрив з'єднання (перемотка відео, закрита вкладка) — не помилка."""
        try:
            super().handle_one_request()
        except (ConnectionError, TimeoutError):
            self.close_connection = True
        except OSError as exc:
            self.close_connection = True
            print(f"  [warn] запит перервано: {exc}", flush=True)

    def log_message(self, format: str, *args: Any) -> None:
        stamp = time.strftime("%H:%M:%S")
        print(f"  {stamp} [{self.address_string()}] {format % args}", flush=True)


def guess_mime(path: Path) -> str:
    return MIME.get(path.suffix.lower(), "application/octet-stream")


def parse_args() -> tuple[int, bool, str]:
    port = DEFAULT_PORT
    open_browser = False
    root = ""
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
            continue
        if arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
            i += 1
            continue
        if arg == "--open":
            open_browser = True
            i += 1
            continue
        if arg == "--root" and i + 1 < len(argv):
            root = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--root="):
            root = arg.split("=", 1)[1]
            i += 1
            continue
        i += 1
    return port, open_browser, root


def main() -> int:
    global PORT_ACTUAL, BASE
    port, open_browser, root = parse_args()
    if root:
        # strip('"') прибирає зайву лапку з "...\" (cmd екранує завершальний бекслеш)
        candidate = Path(root.strip().rstrip('"')).expanduser()
        if not candidate.is_dir():
            print(f"ПОМИЛКА: теку не знайдено: {candidate}", file=sys.stderr)
            return 1
        BASE = candidate.resolve()
    if not GEN_SCRIPT.is_file():
        print(f"ПОМИЛКА: не знайдено {GEN_SCRIPT}", file=sys.stderr)
        return 1
    print(f"Тека матеріалів: {BASE}", flush=True)

    already = find_running_server(port)
    if already is not None:
        url = f"http://{HOST}:{already}/{OUT_NAME}"
        port_file().write_text(str(already) + "\n", encoding="ascii")
        print(f"Сервер уже працює на порту {already}: {url}", flush=True)
        if open_browser:
            import webbrowser
            webbrowser.open(url)
        return 0                # файл порту НЕ видаляємо: сервер не наш

    port = free_port(port)
    PORT_ACTUAL = port
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    httpd.daemon_threads = True
    port_file().write_text(str(port) + "\n", encoding="ascii")
    owns_port_file = True       # цей файл створили ми — при виході приберемо

    url = f"http://{HOST}:{port}/{OUT_NAME}"
    print(f"Сервер перегляду: {url}", flush=True)
    print("Кнопка «🔄 Оновити файли» на сторінці перезапускає генератор.",
          flush=True)
    print("Зупинка: Ctrl+C у цьому вікні.", flush=True)

    if open_browser:
        import webbrowser
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер зупинено.", flush=True)
    finally:
        httpd.server_close()
        try:
            if owns_port_file and \
                    port_file().read_text(encoding="ascii").strip() == str(port):
                port_file().unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
