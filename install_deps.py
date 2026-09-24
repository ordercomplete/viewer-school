#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Перевірка та встановлення залежностей Viewer-for-School.

Викликається двома шляхами (єдина точка правди):
  * інсталятором (Inno Setup, секція [Run]) — після копіювання файлів;
  * start_viewer.bat — перед генерацією сторінки.

Залежності:
  обов'язкова  markdown      — імпортується на рівні модуля в generate_viewer.py;
  опційні      openpyxl      — стилізовані таблиці .xlsx (є stdlib-фолбек);
               python-pptx   — текст слайдів .pptx (є фолбек-картка).
Поза pip (лише діагностика, не встановлюються):
  Microsoft Office (PowerPoint / Word) — JPG-слайди .pptx та PDF для .docx;
  ffmpeg                                — конвертація .avi → .mp4.

Використання:
  python install_deps.py            перевірити й доставити відсутнє
  python install_deps.py --check    лише перевірити (нічого не встановлювати)

Код виходу: 0 — усе гаразд, 1 — немає обов'язкової залежності / не вдалося.
"""
import importlib.util
import io
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast

cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
try:                                  # stderr у UTF-8 — щоб помилки не «кракозябрило»
    cast(io.TextIOWrapper, sys.stderr).reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

MIN_PY = (3, 8)
REQUIRED = {"markdown": "обов'язкова — рендер сторінки"}
OPTIONAL = {"openpyxl": "стилізовані .xlsx",
            "pptx": "текст слайдів .pptx"}
HERE = Path(__file__).resolve().parent
REQS = HERE / "requirements.txt"


def have(module: str) -> bool:
    """Чи імпортується модуль (без побічних ефектів)."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def pip_install() -> bool:
    """Ставить усе з requirements.txt у профіль користувача (--user)."""
    if not REQS.is_file():
        print(f"ПОМИЛКА: не знайдено {REQS}", file=sys.stderr)
        return False
    cmd = [sys.executable, "-m", "pip", "install", "--user",
           "--disable-pip-version-check", "--no-input",
           "-r", str(REQS)]
    print("Встановлення залежностей:", " ".join(cmd[1:]), flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(HERE), check=False)
    except OSError as exc:
        print(f"ПОМИЛКА: не вдалося запустити pip: {exc}", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(f"ПОМИЛКА: pip завершився з кодом {proc.returncode}",
              file=sys.stderr)
        return False
    return True


def office_installed() -> bool:
    """Чи зареєстровані COM-сервери Word і PowerPoint (потрібні для прев'ю)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False
    keys = (
        r"Word.Application\CurVer",
        r"PowerPoint.Application\CurVer",
    )
    found = 0
    for key in keys:
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key):
                found += 1
        except OSError:
            continue
    return found == len(keys)


def report_extras() -> None:
    """Підказки про ПЗ, яке не ставиться через pip."""
    if office_installed():
        print("• Microsoft Office: знайдено — JPG-слайди .pptx і PDF для .docx "
              "працюватимуть.")
    else:
        print("• Microsoft Office: НЕ знайдено — слайди .pptx показуватимуться "
              "без зображень, для .docx залишиться HTML-режим.")
        print("  (Office встановлюється окремо; інсталятор не має права "
              "встановлювати його автоматично)")
    if shutil.which("ffmpeg"):
        print("• ffmpeg: знайдено — .avi конвертуватиметься у .mp4.")
    else:
        print("• ffmpeg: НЕ знайдено — .avi відкриватиметься окремо. "
              "За потреби: https://ffmpeg.org/download.html або "
              "winget install Gyan.FFmpeg.Essentials")


def main() -> int:
    check_only = "--check" in sys.argv

    if sys.version_info < MIN_PY:
        print(f"ПОМИЛКА: потрібен Python {MIN_PY[0]}.{MIN_PY[1]}+, "
              f"а запущено {sys.version.split()[0]}", file=sys.stderr)
        return 1

    missing_req = [m for m in REQUIRED if not have(m)]
    missing_opt = [m for m in OPTIONAL if not have(m)]

    if missing_req or missing_opt:
        for mod in missing_req:
            print(f"◦ немає {mod} ({REQUIRED[mod]})")
        for mod in missing_opt:
            print(f"◦ немає {mod} ({OPTIONAL[mod]}) — опційно")
        if check_only:
            print("Режим --check: нічого не встановлюю.")
        elif not pip_install():
            return 1
        else:
            missing_req = [m for m in REQUIRED if not have(m)]
            missing_opt = [m for m in OPTIONAL if not have(m)]
    else:
        print("Усі Python-залежності вже встановлені.")

    print("Стан:")
    print("  обов'язкові: " + (", ".join(REQUIRED) or "—") +
          (" — ок" if not missing_req else " — ВІДСУТНІ"))
    print(f"  опційні: {', '.join(OPTIONAL)}" +
          (" — ок" if not missing_opt else
           f" — немає: {', '.join(missing_opt)}"))
    report_extras()

    if missing_req:
        print("ПОМИЛКА: без обов'язкових залежностей генерація неможлива.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
