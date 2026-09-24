# -*- coding: utf-8 -*-
"""
Генератор viewer.html — сторінки-переглядача вмісту папки навчальних матеріалів.
Створює самодостатній HTML із деревом папок ліворуч і фреймом перегляду праворуч.
Запуск: python generate_viewer.py  (або через start_viewer.bat)
"""
import sys
import io
import csv
import json
import html
import zipfile
import re
import os
import base64
import hashlib
import subprocess
import xml.etree.ElementTree as ET
import markdown
from datetime import date, datetime
from pathlib import Path
from typing import cast, Any
from urllib.parse import quote

cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding="utf-8")
try:                                  # stderr у UTF-8 — щоб помилки не «кракозябрило»
    cast(io.TextIOWrapper, sys.stderr).reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def resolve_base() -> Path:
    """Тека матеріалів: аргумент запуску → тека скриптів.

    Пріоритет:
      1) перший аргумент-каталог — `python generate_viewer.py "<тека>"`;
      2) тека, у якій лежить сам скрипт (портативне встановлення).
    Типово обидва варіанти збігаються — генерація «у поточній теці».
    """
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            continue                       # --prewarm тощо
        # strip('"') прибирає зайву лапку з "...\" (.cmd екранує завершальний
        # бекслеш) — інакше Path рахує такий шлях неіснуючим
        candidate = Path(arg.strip().rstrip('"')).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    return Path(__file__).resolve().parent


BASE = resolve_base()
OUT_NAME = "viewer.html"
EXCLUDE_FILES = {"generate_viewer.py", "start_viewer.bat",
                 "viewer_server.py", "viewer_probe.py",
                 "install_deps.py", "generate_for.bat",
                 "requirements.txt", "LICENSE.txt", "VERSION",
                 "INSTALLER_PLAN.md",
                 OUT_NAME, OUT_NAME + ".tmp"}   # службові файли
EXCLUDE_PREFIXES = ("viewer_server.",)   # port/log — і будь-які ротації
TEMP_PREFIX = "_"  # тимчасові/тестові артефакти не показуємо в дереві
ASSETS = BASE / "viewer_assets"  # зображення pptx/docx, конвертовані avi

# ---------------------------------------------------------------- текст опису
HELP_MD_PATH = BASE / "viewer_help.md"   # вставляється у вітальну сторінку

# ---------------------------------------------------------------- утиліти

def human_size(n: int) -> str:
    size = float(n)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024 or unit == "ГБ":
            return f"{size:.0f} {unit}" if unit == "Б" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ГБ"


ICONS = {
    ".md": "📝", ".pdf": "📕", ".mp4": "🎬", ".avi": "🎞️",
    ".pptx": "📊", ".ppt": "📊", ".docx": "📃", ".gif": "🖼️",
    ".html": "🌐", ".htm": "🌐", ".jar": "🔷", ".xlsx": "📈",
    ".csv": "📈", ".xls": "📈",
    ".txt": "📄",
}

# Розширення з власним прев'ю (решта → картка «Відкрити окремо»).
KNOWN_PREVIEW_EXTS = {
    ".md", ".pdf", ".mp4", ".avi", ".pptx", ".ppt", ".docx", ".gif",
    ".html", ".htm", ".jar", ".xlsx", ".csv", ".xls", ".txt",
}


def icon_for(name: str) -> str:
    return ICONS.get(Path(name).suffix.lower(), "📄")


def _inline_markdown(text: str) -> str:
    """Обробляє інлайн-разметку Markdown: **жирний**, *курсив*, `код`, [текст](url)."""
    import re as _re
    
    # Спочатку екрануємо HTML-символи (щоб уникнути XSS)
    text = html.escape(text)
    
    # Посилання [текст](url) — повертаємо HTML-тег
    text = _re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Код `...` — повертаємо HTML-тег
    text = _re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Жирний **...**
    text = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Курсив *...*
    text = _re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', text)
    # Курсив _..._
    text = _re.sub(r'(?<!_)_([^_\n]+)_(?!_)', r'<i>\1</i>', text)
    
    return text


def _table(rows: list[list[str]], head: bool = False) -> str:
    """Матриця рядків → HTML-таблиця."""
    out = ["<table class=\"grid\">"]
    for i, row in enumerate(rows):
        cells = []
        for value in row:
            tag = "th" if (head and i == 0) else "td"
            cells.append(f"<{tag}>{_cell_text(value)}</{tag}>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "".join(out)


def _cell_text(value: str) -> str:
    """Комірка таблиці → безпечний текст."""
    return html.escape(value or "")
def rel_url(path: Path) -> str:
    """Відносний URL файлу від папки progect-viewer-school.

    Працює і для сторінки, відкритої як file:///…/viewer.html,
    і для сторінки, розданої локальним сервером (http://127.0.0.1:…).
    """
    try:
        rel = path.resolve().relative_to(BASE).as_posix()
    except ValueError:                       # поза папкою progect-viewer-school
        rel = path.as_posix()
    return quote(rel)


# --------------------------------------------------- ресурси (viewer_assets)

def asset_file(blob: bytes, ext: str) -> Path:
    """Зберігає blob у viewer_assets/ з ім'ям за md5 (кеш повторних запусків)."""
    ASSETS.mkdir(exist_ok=True)
    dst = ASSETS / (hashlib.md5(blob).hexdigest()[:16] + ext)
    if not dst.exists() or dst.stat().st_size != len(blob):
        dst.write_bytes(blob)
    return dst


def convert_avi(src: Path) -> Path | None:
    """Конвертує AVI у MP4 через ffmpeg для відтворення у браузері."""
    out_dir = ASSETS / "video"
    out_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(str(src).encode("utf-8")).hexdigest()[:16]
    dst = out_dir / (key + ".mp4")
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst  # кеш: вже конвертовано
    cmd = ["ffmpeg", "-y", "-i", str(src),
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-c:a", "aac", "-movflags", "+faststart", str(dst)]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=600)
        if r.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
            return dst
    except Exception:
        pass
    if dst.exists():
        dst.unlink(missing_ok=True)
    return None


# ------------------------------------- Office-експорт (PowerPoint / Word COM)

_EXPORT_FAILED: set[str] = set()  # невдалі експорті цього запуску

_PS_BATCH = r"""
$ErrorActionPreference = 'Stop'
$pp = $null
$word = $null
Get-Content -Encoding UTF8 $env:PV_JOBS | ForEach-Object {
    if (-not $_) { return }
    $p = $_ -split "`t"
    $kind = $p[0]; $src = $p[1]; $out = $p[2]
    try {
        if ($kind -eq 'slides') {
            New-Item -ItemType Directory -Force -Path $out | Out-Null
            if ($null -eq $pp) { $pp = New-Object -ComObject PowerPoint.Application }
            $pres = $pp.Presentations.Open($src, -1, 0, 0)
            try {
                try {
                    $sw = [int](($pres.PageSetup.SlideWidth / 72) * 144)
                    $sh = [int](($pres.PageSetup.SlideHeight / 72) * 144)
                    $pres.Export($out, 'JPG', $sw, $sh)
                } catch { $pres.Export($out, 'JPG') }
            } finally { $pres.Close() }
            Set-Content -Path (Join-Path $out '.done') -Value 'ok' -Encoding ascii
        } elseif ($kind -eq 'pdf') {
            $dir = Split-Path $out -Parent
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
            if ($null -eq $word) { $word = New-Object -ComObject Word.Application; $word.Visible = $false }
            $doc = $word.Documents.Open($src, $false, $true)
            try { $doc.ExportAsFixedFormat($out, 17) } finally { $doc.Close(0) }
        }
    } catch {
        Write-Output ('ERR ' + $src + ': ' + $_.Exception.Message)
    }
}
if ($pp -ne $null) { try { $pp.Quit() } catch {} }
if ($word -ne $null) { try { $word.Quit() } catch {} }
exit 0
"""


def _cache_key(path: Path) -> str:
    st = path.stat()
    raw = f"{path}|{st.st_mtime}|{st.st_size}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _ps_run(script: str, env: dict) -> bool:
    e = dict(os.environ)
    e.update(env)
    try:
        b64 = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-EncodedCommand", b64],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=e, timeout=1800)
        if r.returncode != 0 or "ERR " in (r.stdout or ""):
            lines = (r.stderr or r.stdout or "").strip().splitlines()
            print("  PS:", lines[0] if lines else f"rc={r.returncode}",
                  flush=True)
        return r.returncode == 0
    except Exception as e:
        print("  PS виняток:", e, flush=True)
        return False


def _run_jobs(jobs: list) -> None:
    if not jobs:
        return
    ASSETS.mkdir(exist_ok=True)
    jf = ASSETS / "jobs.tsv"
    jf.write_text("\n".join("\t".join(j) for j in jobs) + "\n",
                  encoding="utf-8")
    _ps_run(_PS_BATCH, {"PV_JOBS": str(jf)})


def _fresh(marker: Path, src: Path) -> bool:
    try:
        return (marker.exists()
                and marker.stat().st_mtime >= src.stat().st_mtime)
    except OSError:
        return False


def _slide_files(out_dir: Path) -> list:
    if not out_dir.is_dir():
        return []
    files = [p for p in out_dir.iterdir()
             if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}]

    def num(p: Path) -> int:
        m = re.search(r"(\d+)", p.stem)
        return int(m.group(1)) if m else 0

    return sorted(files, key=num)


def export_office_slides(path: Path) -> list | None:
    """JPG-слайди презентації (pptx/ppt) через PowerPoint; None якщо fail."""
    if str(path) in _EXPORT_FAILED:
        return None
    out_dir = ASSETS / "slides" / _cache_key(path)
    if _fresh(out_dir / ".done", path):
        files = _slide_files(out_dir)
        if files:
            return files
    _run_jobs([("slides", str(path), str(out_dir))])
    if _fresh(out_dir / ".done", path):
        files = _slide_files(out_dir)
        if files:
            return files
    _EXPORT_FAILED.add(str(path))
    return None


def export_docx_pdf(path: Path) -> Path | None:
    """PDF для docx через Word (оригінальне форматування); None якщо fail."""
    if str(path) in _EXPORT_FAILED:
        return None
    dst = ASSETS / "docs" / (_cache_key(path) + ".pdf")
    if dst.exists() and dst.stat().st_mtime >= path.stat().st_mtime:
        return dst
    _run_jobs([("pdf", str(path), str(dst))])
    if dst.exists() and dst.stat().st_mtime >= path.stat().st_mtime:
        return dst
    _EXPORT_FAILED.add(str(path))
    return None


def prewarm_office_exports(base: Path) -> None:
    """Пакетний експорт усіх pptx/ppt → JPG і docx → PDF одним сеансом Office."""
    jobs: list = []
    for p in sorted(base.rglob("*")):
        if not p.is_file() or p.name.startswith("~$"):
            continue
        if ASSETS in p.parents:
            continue
        ext = p.suffix.lower()
        if ext in {".pptx", ".ppt"}:
            out_dir = ASSETS / "slides" / _cache_key(p)
            if not (_fresh(out_dir / ".done", p) and _slide_files(out_dir)):
                jobs.append(("slides", str(p), str(out_dir)))
        elif ext == ".docx":
            dst = ASSETS / "docs" / (_cache_key(p) + ".pdf")
            if not (dst.exists()
                    and dst.stat().st_mtime >= p.stat().st_mtime):
                jobs.append(("pdf", str(p), str(dst)))
    if not jobs:
        return
    print(f"Office-експорт: {len(jobs)} завдань...", flush=True)
    for i in range(0, len(jobs), 10):
        _run_jobs(jobs[i:i + 10])
        print(f"  ...{min(i + 10, len(jobs))}/{len(jobs)}", flush=True)
    for kind, src, out in jobs:
        sp = Path(src)
        if kind == "pdf":
            ok = (Path(out).exists()
                  and Path(out).stat().st_mtime >= sp.stat().st_mtime)
        else:
            ok = (_fresh(Path(out) / ".done", sp)
                  and bool(_slide_files(Path(out))))
        if not ok:
            _EXPORT_FAILED.add(str(sp))
            print(f"  WARN експорт не вдався: {sp.name}", flush=True)
    print("Office-експорт завершено.", flush=True)


def render_slides_preview(slide_files: list, slide_html: list) -> str:
    """HTML із зображеннями слайдів (оригінальний вигляд) + текст."""
    parts = []
    for i, sp in enumerate(slide_files, 1):
        img = (f'<img class="slideimg" src="{rel_url(sp)}" alt="Слайд {i}"'
               f' loading="lazy">')
        txt = slide_html[i - 1] if i - 1 < len(slide_html) else ""
        det = ""
        if txt:
            det = (f'<details><summary>Текст слайда {i}</summary>'
                   f'<div class="stext">{txt}</div></details>')
        parts.append(f'<section class="slide"><h3>Слайд {i}</h3>'
                     f'{img}{det}</section>')
    return "".join(parts)


# ------------------------------------------------------- витяг вмісту файлів

def render_md(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "nl2br"])
    return wrap_doc(path.name, f'<article class="md">{body}</article>')


def render_pptx(path: Path) -> str:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs = Presentation(str(path))
    slide_html: list = []

    def collect_pics(shapes: Any) -> list:
        found = []
        for sh in shapes:
            st = getattr(sh, "shape_type", None)
            if st == MSO_SHAPE_TYPE.PICTURE:
                found.append(sh)
            elif st == MSO_SHAPE_TYPE.GROUP:
                found.extend(collect_pics(getattr(sh, "shapes", [])))
        return found

    for slide in prs.slides:
        texts = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                tf: Any = getattr(shape, "text_frame")
                for para in tf.paragraphs:
                    t = "".join(run.text for run in para.runs).strip()
                    if t:
                        texts.append(t)
            if getattr(shape, "has_table", False):
                tbl: Any = getattr(shape, "table")
                rows = []
                for row in tbl.rows:
                    cells = [html.escape(c.text.strip()) for c in row.cells]
                    rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
                texts.append("<table>" + "".join(rows) + "</table>")
        joined = ""
        if texts:
            joined = "<br>\n".join(
                f"<div>{html.escape(t)}</div>" if not t.startswith("<table") else t
                for t in texts
            )
        pics = []
        for sh in collect_pics(slide.shapes):
            try:
                img: Any = getattr(sh, "image")
                ext = "." + (getattr(img, "ext", None) or "png")
                dst = asset_file(getattr(img, "blob"), ext)
                alt = html.escape(str(getattr(sh, "name", "") or ""))
                pics.append(f'<img src="{rel_url(dst)}" alt="{alt}" loading="lazy">')
            except Exception:
                continue
        if pics:
            joined += '<div class="pics">' + "".join(pics) + "</div>"
        slide_html.append(joined)

    body = f'<h2>{html.escape(path.name)}</h2>'
    slide_files = export_office_slides(path)
    if slide_files:
        body += render_slides_preview(slide_files, slide_html)
    else:
        parts = [f'<section class="slide"><h3>Слайд {i}</h3>{s}</section>'
                 for i, s in enumerate(slide_html, 1) if s]
        if not parts:
            parts = ["<p><i>Текст у файлі не знайдено "
                     "(можливо, лише зображення).</i></p>"]
        body += "".join(parts)
    return wrap_doc(path.name, f'<article class="doc">{body}</article>')


def _docx_ns(tag: str) -> str:
    return "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}" + tag


def _docx_run_html(r: Any) -> str:
    txt = "".join(t.text or "" for t in r.iter(_docx_ns("t")))
    if not txt:
        if any(True for _ in r.iter(_docx_ns("tab"))):
            return "\t"
        if any(True for _ in r.iter(_docx_ns("br"))):
            return "<br>"
        return ""
    esc = html.escape(txt)
    styles: list[str] = []
    props = r.find(_docx_ns("rPr"))
    bold = ital = undl = False
    if props is not None:
        bold = props.find(_docx_ns("b")) is not None
        ital = props.find(_docx_ns("i")) is not None
        undl = props.find(_docx_ns("u")) is not None
        for sz in props.iter(_docx_ns("sz")):
            try:
                v = max(8, min(48, round(int(sz.get("val", "24")) / 2)))
                styles.append(f"font-size:{v}px")
            except (TypeError, ValueError):
                pass
            break
        for c in props.iter(_docx_ns("color")):
            v = c.get("val", "")
            if len(v) == 6 and v != "auto":
                styles.append(f"color:#{v}")
            break
    if bold:
        esc = f"<b>{esc}</b>"
    if ital:
        esc = f"<i>{esc}</i>"
    if undl:
        esc = f"<u>{esc}</u>"
    if styles:
        esc = f'<span style="{";".join(styles)}">{esc}</span>'
    return esc


def _docx_para_html(p: Any, bullets: dict[str, str] | None,
                    hrefs: dict[str, str] | None = None) -> str:
    tag, cls, pre = "p", "", ""
    ppr = p.find(_docx_ns("pPr"))
    align = ""
    if ppr is not None:
        for st in ppr.iter(_docx_ns("pStyle")):
            v = st.get("val", "")
            if v == "Title":
                tag = "h1"
            elif v in ("Heading1", "1"):
                tag = "h2"
            elif v in ("Heading2", "Heading3", "2", "3"):
                tag = "h3"
            break
        for jc in ppr.iter(_docx_ns("jc")):
            a = jc.get("val", "")
            if a == "center":
                align = "text-align:center"
            elif a == "right":
                align = "text-align:right"
            elif a == "both":
                align = "text-align:justify"
            break
        for np in ppr.iter(_docx_ns("numPr")):
            nid = ilvl = None
            for i in np.iter(_docx_ns("numId")):
                nid = i.get("val")
            for i in np.iter(_docx_ns("ilvl")):
                ilvl = i.get("val", "0")
            mark = (bullets or {}).get(f"{nid}/{ilvl}", "•")
            pre = f'<span class="lm">{html.escape(mark)}</span>'
            cls = f"lil{ilvl}"
            break
    runs = "".join(_docx_run_html(r)
                   for r in p.findall(_docx_ns("r")))
    links = ""
    for hl in p.findall(_docx_ns("hyperlink")):
        rid = hl.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        url = ((hrefs or {}).get(rid, "") if rid else "")
        txt = "".join(_docx_run_html(r) for r in hl.findall(_docx_ns("r")))
        if url:
            txt = f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">{txt}</a>'
        links += txt
    if not runs.replace("<br>", "").replace("\t", "").strip() \
            and not links and not pre:
        return ""
    at = f' class="{cls}"' if cls else ""
    if align:
        at += f' style="{align}"'
    return f"<{tag}{at}>{pre}{runs}{links}</{tag}>"


def _docx_tbl_html(tbl: Any, bullets: dict[str, str] | None,
                   hrefs: dict[str, str] | None = None) -> str:
    out = ['<table class="dt">']
    for row in tbl.iter(_docx_ns("tr")):
        out.append("<tr>")
        for cell in row.iter(_docx_ns("tc")):
            span = ""
            for gs in cell.iter(_docx_ns("gridSpan")):
                try:
                    v = int(gs.get("val", "1"))
                    if v > 1:
                        span = f" colspan={v}"
                except (TypeError, ValueError):
                    pass
                break
            inner = "".join(_docx_para_html(x, bullets, hrefs)
                            for x in cell.findall(_docx_ns("p")))
            out.append(f"<td{span}>{inner or '&nbsp;'}</td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def render_docx_html(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        doc = ET.fromstring(zf.read("word/document.xml"))
        bullets: dict[str, str] = {}
        if "word/numbering.xml" in names:
            try:
                nroot = ET.fromstring(zf.read("word/numbering.xml"))
                absnum: dict[str, Any] = {}
                for an in nroot.iter(_docx_ns("abstractNum")):
                    aid = an.get(_docx_ns("abstractNumId"))
                    for lvl in an.iter(_docx_ns("lvl")):
                        il = lvl.get(_docx_ns("ilvl"), "0")
                        fm = st = None
                        for f in lvl.iter(_docx_ns("numFmt")):
                            fm = f.get(_docx_ns("val"))
                        for s in lvl.iter(_docx_ns("start")):
                            st = s.get(_docx_ns("val"), "1")
                        absnum[f"{aid}/{il}"] = (fm or "bullet", st or "1")
                for ni in nroot.iter(_docx_ns("num")):
                    nid = ni.get(_docx_ns("numId"))
                    aid = None
                    for a in ni.iter(_docx_ns("abstractNumId")):
                        aid = a.get(_docx_ns("val"))
                    for il in range(9):
                        hit = absnum.get(f"{aid}/{il}")
                        if hit:
                            fm, st = hit
                            try:
                                bullets[f"{nid}/{il}"] = (
                                    "•" if fm == "bullet" else f"{int(st)}.")
                            except (TypeError, ValueError):
                                bullets[f"{nid}/{il}"] = "•"
            except ET.ParseError:
                pass
        media = []
        rels: dict[str, str] = {}
        if "word/_rels/document.xml.rels" in names:
            try:
                rroot = ET.fromstring(zf.read("word/_rels/document.xml.rels"))
                for r in rroot.iter("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                    if r.get("Type", "").endswith("/hyperlink"):
                        rels[r.get("Id", "")] = r.get("Target", "")
            except ET.ParseError:
                pass
        for n in names:
            if n.startswith("word/media/"):
                blob = zf.read(n)
                ext = Path(n).suffix.lower() or ".png"
                media.append(
                    f'<div class="pics"><img src="{rel_url(asset_file(blob, ext))}"'
                    f' alt="" loading="lazy"></div>')
    blocks = []
    body = doc.find(_docx_ns("body"))
    for el in body if body is not None else []:
        if el.tag == _docx_ns("p"):
            blocks.append(_docx_para_html(el, bullets, rels))
        elif el.tag == _docx_ns("tbl"):
            blocks.append(_docx_tbl_html(el, bullets, rels))
    css = ("<style>.dt{border-collapse:collapse;margin:8px 0}"
           ".dt td{border:1px solid #999;padding:3px 8px}"
           ".lm{color:#0b5cad;margin-right:6px}"
           ".lil0{margin-left:18px}.lil1{margin-left:42px}"
           ".lil2{margin-left:66px}.lil3{margin-left:90px}"
           ".pics img{max-width:100%}</style>")
    inner = "".join(blocks) + "".join(media)
    return wrap_doc(path.name, f"<article class='doc'>{css}{inner}</article>")


def render_docx(path: Path) -> str:
    """Сумісність: текстовий варіант (див. також render_docx_html)."""
    media_html = []
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        for n in z.namelist():
            if n.startswith("word/media/"):
                blob = z.read(n)
                ext = Path(n).suffix.lower() or ".png"
                media_html.append(
                    f'<div class="pics"><img src="{rel_url(asset_file(blob, ext))}"'
                    f' alt="" loading="lazy"></div>')
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = re.sub(r"<w:br[^>]*/>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    text = html.unescape(xml)

    def fmt(line: str) -> str:
        esc = html.escape(line.strip())
        esc = re.sub(r"(https?://[^\s<]+)",
                     r'<a href="\1" target="_blank" rel="noopener">\1</a>', esc)
        return f"<p>{esc}</p>"

    paras = "".join(fmt(line) for line in text.splitlines() if line.strip())
    body = (f"<h2>{html.escape(path.name)}</h2>"
            + (paras or "<p><i>Порожній документ.</i></p>")
            + "".join(media_html))
    return wrap_doc(path.name, f'<article class="doc">{body}</article>')


def _col_index(ref: str) -> int:
    """«C7» → 2 (індекс колонки з нуля)."""
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        elif n:
            break
    return max(n - 1, 0)


def _xlsx_rows(z: zipfile.ZipFile, name: str, shared: list[str],
               max_rows: int, max_cols: int) -> list[list[str]]:
    """Читає аркуш xlsx → матриця текстових значень (до max_rows×max_cols)."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    root = ET.fromstring(z.read(name))
    rows: list[list[str]] = []
    for tr in root.iter(f"{ns}row"):
        if len(rows) >= max_rows:
            break
        values: dict[int, str] = {}
        for c in tr.findall(f"{ns}c"):
            t = c.get("t")
            txt = ""
            if t == "inlineStr":
                node = c.find(f"{ns}is")
                if node is not None:
                    txt = "".join(x.text or "" for x in node.iter(f"{ns}t"))
            else:
                v = c.find(f"{ns}v")
                if v is not None and v.text is not None:
                    if t == "s":
                        idx = int(v.text)
                        txt = shared[idx] if 0 <= idx < len(shared) else ""
                    elif t == "b":
                        txt = "ТАК" if v.text == "1" else "НІ"
                    else:
                        txt = v.text
            if not txt:
                continue
            col = _col_index(c.get("r") or "")
            if col < max_cols:
                values[col] = txt
        if values:
            row = [html.escape(values.get(i, "")) for i in range(max(values) + 1)]
            rows.append(row)
    return rows


def render_xlsx_stdlib(path: Path, max_rows: int = 200,
                       max_cols: int = 30) -> str:
    """Запасний варіант .xlsx без залежностей (zipfile + XML).

    Використовується, якщо не встановлено openpyxl.
    """
    sections = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{ns}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{ns}t")))
        titles: dict[str, str] = {}
        if "xl/workbook.xml" in names:
            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            for i, sh in enumerate(wb.iter(f"{ns}sheet"), 1):
                titles[f"xl/worksheets/sheet{i}.xml"] = str(sh.get("name") or "")
        books = sorted(n for n in names
                       if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        for i, name in enumerate(books, 1):
            rows = _xlsx_rows(z, name, shared, max_rows, max_cols)
            title = titles.get(name) or f"Аркуш {i}"
            if not rows:
                sections.append(f"<h3>{html.escape(title)}</h3>"
                                "<p><i>Порожній аркуш.</i></p>")
                continue
            width = max(len(r) for r in rows)
            body = ['<table class="sheet"><tbody>']
            for r_i, row in enumerate(rows):
                cells = row + [""] * (width - len(row))
                tag = "th" if r_i == 0 else "td"
                body.append("<tr>" + "".join(
                    f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            body.append("</tbody></table>")
            info = ""
            if len(rows) >= max_rows or width >= max_cols:
                info = (f'<p class="hint">Показано перші {len(rows)} рядків × '
                        f"{width} стовпців.</p>")
            sections.append(f"<h3>{html.escape(title)}</h3>"
                            + "".join(body) + info)
    note = ('<p class="hint">Перший рядок показано як заголовок. '
            'Повне форматування — у Excel.</p>')
    body = f"<h2>{html.escape(path.name)}</h2>" + note + "".join(sections)
    return wrap_doc(path.name, f'<article class="doc">{body}</article>')


def _cell_text(value: Any) -> str:
    """Значення комірки → безпечний HTML-текст."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d.%m.%Y")
    return html.escape(str(value))


def _table(rows: list[list[Any]], head: bool = False) -> str:
    """Матриця значень → HTML-таблиця (перший рядок може бути заголовком)."""
    out = ["<table class=\"grid\">"]
    for i, row in enumerate(rows):
        cells = []
        for value in row:
            tag = "th" if (head and i == 0) else "td"
            cells.append(f"<{tag}>{_cell_text(value)}</{tag}>")
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</table>")
    return "".join(out)


def _trim(rows: list[list[Any]]) -> list[list[Any]]:
    """Прибирає порожні рядки/стовпці з кінця (Excel часто має зайві)."""
    while rows and all(c in (None, "") for c in rows[-1]):
        rows.pop()
    while rows and rows[0] and rows[0][-1] in (None, ""):
        if all((len(r) < len(rows[0])) or r[-1] in (None, "") for r in rows):
            for r in rows:
                if len(r) == len(rows[0]):
                    r.pop()
        else:
            break
    return rows


def _xlsx_hex(color: Any) -> str | None:
    """ARGB-рядок openpyxl → '#RRGGBB' (тільки явні кольори, без тем)."""
    try:
        rgb = getattr(color, "rgb", None)
    except (ValueError, TypeError):
        return None
    if not isinstance(rgb, str) or len(rgb) != 8:
        return None
    if not all(ch in "0123456789ABCDEFabcdef" for ch in rgb):
        return None
    return "#" + rgb[2:]


def _hex_luminance(hex_color: str) -> float:
    """Обчислює яскравість кольору (0 = чорний, 1 = білий)."""
    r = int(hex_color[1:3], 16) / 255.0
    g = int(hex_color[3:5], 16) / 255.0
    b = int(hex_color[5:7], 16) / 255.0
    # Формула WCAG relative luminance
    return 0.299 * r + 0.587 * g + 0.114 * b


def _contrast_color(bg_hex: str) -> str:
    """Повертає чорний або білий колір залежно від яскравості фону."""
    if _hex_luminance(bg_hex) < 0.5:
        return "#000000"  # темний фон → чорний шрифт
    return "#1a1a1a"  # світлий фон → темний шрифт

def render_xlsx(path: Path) -> str:
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter
    wb = load_workbook(path, data_only=False)
    parts = [f"<h2>{html.escape(path.name)}</h2>"]
    limit_rows, limit_cols = 500, 40
    css: dict[str, str] = {}
    classes: dict[str, str] = {}

    def css_class(key: str, rules: str) -> str:
        if key not in classes:
            classes[key] = f"xs{len(classes)}"
            css[classes[key]] = rules
        return classes[key]

    border_w = {"thin": "1px", "medium": "2px", "thick": "3px",
                "double": "3px", "dashed": "1px", "dotted": "1px"}

    def fmt_cell(c: Any) -> str:
        rules: list[str] = []
        f = c.font
        if f.bold:
            rules.append("font-weight:bold")
        if f.italic:
            rules.append("font-style:italic")
        if f.underline and f.underline != "none":
            rules.append("text-decoration:underline")
        if f.size:
            try:
                sz = max(8, min(28, round(float(f.size))))
                rules.append(f"font-size:{sz}px")
            except (TypeError, ValueError):
                pass
        col = _xlsx_hex(f.color)
        has_explicit_font_color = bool(col)
        if col:
            rules.append(f"color:{col}")
        fl = c.fill
        cell_bg = None
        if getattr(fl, "patternType", None) == "solid":
            bg = _xlsx_hex(fl.fgColor)
            if bg:
                rules.append(f"background:{bg}")
                cell_bg = bg
        # Коли комірка має темний фон — підібрати контрастний шрифт
        if cell_bg:
            lum = _hex_luminance(cell_bg)
            if lum < 0.5:
                # Темний фон → світлий шрифт
                rules.append("color:#ffffff")
            elif lum < 0.7:
                # Середній фон → темно-сірий шрифт
                rules.append("color:#1a1a1a")
            # Світлий фон (lum >= 0.7) — темний шрифт за замовчуванням
        # Дефолтний шрифт для комірок без експліцитного кольору
        if not has_explicit_font_color:
            rules.append("color:#1a1a1a")
        al = c.alignment
        if al.horizontal in ("left", "center", "right"):
            rules.append(f"text-align:{al.horizontal}")
        if al.vertical == "center":
            rules.append("vertical-align:middle")
        elif al.vertical == "top":
            rules.append("vertical-align:top")
        if al.wrap_text:
            rules.append("white-space:normal")
        bd = c.border
        for side in ("left", "top", "right", "bottom"):
            st = getattr(getattr(bd, side, None), "style", None)
            if st in border_w:
                rules.append(f"border-{side}:{border_w[st]} solid #444")
        key = "|".join(rules)
        return css_class(key, ";".join(rules)) if key else ""

    for ws in wb.worksheets:
        mx_r = min(ws.max_row or 0, limit_rows)
        mx_c = min(ws.max_column or 0, limit_cols)
        if mx_r == 0 or mx_c == 0:
            parts.append(f"<h3>{html.escape(ws.title)}</h3><p>(порожній аркуш)</p>")
            continue
        parts.append(f"<h3>{html.escape(ws.title)}</h3>")
        col_w = []
        for ci in range(1, mx_c + 1):
            w = ws.column_dimensions[get_column_letter(ci)].width
            px = max(28, min(420, round((w or 8.43) * 7))) if w else 64
            col_w.append(f'<col style="width:{px}px">')
        parts.append(f'<table class="xst">{"".join(col_w)}')
        merged = ws.merged_cells.ranges
        covered: set[tuple[int, int]] = set()
        rng_of: dict[tuple[int, int], Any] = {}
        for rng in merged:
            for rr in range(rng.min_row, rng.max_row + 1):
                for cc in range(rng.min_col, rng.max_col + 1):
                    if (rr, cc) != (rng.min_row, rng.min_col):
                        covered.add((rr, cc))
            rng_of[(rng.min_row, rng.min_col)] = rng
        for r in range(1, mx_r + 1):
            rh = ws.row_dimensions[r].height
            if rh:
                parts.append(f'<tr style="height:{max(14, round(rh * 1.33))}px">')
            else:
                parts.append("<tr>")
            for ci in range(1, mx_c + 1):
                if (r, ci) in covered:
                    continue
                c = ws.cell(row=r, column=ci)
                val = "" if c.value is None else str(c.value)
                attrs = ""
                rng = rng_of.get((r, ci))
                if rng is not None:
                    rs = rng.max_row - rng.min_row + 1
                    cs = rng.max_col - rng.min_col + 1
                    if rs > 1:
                        attrs += f" rowspan={rs}"
                    if cs > 1:
                        attrs += f" colspan={cs}"
                cls = fmt_cell(c)
                if cls:
                    attrs += f' class="{cls}"'
                parts.append(f"<td{attrs}>{html.escape(val)}</td>")
            parts.append("</tr>")
        parts.append("</table>")
        if ws.max_row > limit_rows or ws.max_column > limit_cols:
            parts.append(f"<p>…показано перші {limit_rows}×{limit_cols} "
                         f"(усього {ws.max_row}×{ws.max_column})</p>")
    wb.close()
    style = "".join(f".xst .{n}{{{r}}}" for n, r in css.items())
    css_head = ("<style>.xst{border-collapse:collapse;background:#fff}"
                ".xst td{border:1px solid #999;padding:2px 5px;white-space:nowrap}")
    body = css_head + style + "</style>" + "".join(parts)
    return wrap_doc(path.name, body)


def render_csv(path: Path) -> str:
    """CSV → HTML-таблиця."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
    rows = [row for row in csv.reader(io.StringIO(text), dialect)]
    rows = _trim(rows)
    body = (f"<h2>{html.escape(path.name)}</h2>"
            + (_table(rows, head=True) if rows
               else "<p><i>Порожній файл.</i></p>"))
    return wrap_doc(path.name, f'<article class="doc">{body}</article>')


def info_card(path: Path, note: str) -> str:
    st = path.stat()
    uri = rel_url(path)
    body = f"""
    <div class="card">
      <div class="card-icon">{icon_for(path.name)}</div>
      <h2>{html.escape(path.name)}</h2>
      <table class="meta">
        <tr><th>Тип</th><td>{html.escape(path.suffix.lower() or "без розширення")}</td></tr>
        <tr><th>Розмір</th><td>{human_size(st.st_size)}</td></tr>
        <tr><th>Шлях</th><td>{html.escape(str(path))}</td></tr>
      </table>
      <p class="note">{note}</p>
      <p><a class="btn" href="{uri}">Відкрити у системі</a></p>
      <p class="hint">Якщо браузер пропонує завантажити — відкрийте файл після
      завантаження або через Провідник.</p>
    </div>"""
    return wrap_doc(path.name, body)


def avi_video_card(path: Path) -> str:
    uri = rel_url(path)
    body = f"""
    <div class="card" style="max-width:960px">
      <h2>{html.escape(path.name)}</h2>
      <video controls preload="metadata" src="{uri}"></video>
      <p class="note">Формат AVI не завжди підтримується браузером.
      Якщо відео не відтворюється —
      <a href="{uri}">відкрити у системному плеєрі</a>.</p>
    </div>"""
    return wrap_doc(path.name, body)


def welcome_doc() -> str:
    """Генерує вітальну сторінку з поясненням і покажчиком viewer_help.md."""
    # Спроба завантажити viewer_help.md з диска
    help_md_path = HELP_MD_PATH
    help_html = ""
    if help_md_path.exists():
        try:
            md_text = help_md_path.read_text(encoding="utf-8")
            # Конвертуємо Markdown у HTML повноцінним рендерером
            help_html = markdown.markdown(md_text, extensions=["tables", "fenced_code", "nl2br"])
        except Exception:
            pass

    return wrap_doc("Ласкаво просимо", f"""
    <div class="card">
      <div class="card-icon">📚</div>
      <h2>Viewer-for-School — навчальні матеріали 11-Д</h2>
      <p>Оберіть файл зліва у дереві — його вміст відкриється у цьому фреймі.</p>
      <ul>
        <li>📝 <b>.md</b> — рендериться з форматуванням;</li>
        <li>📕 <b>.pdf</b>, 🌐 <b>.html</b> — відкриваються у фреймі;</li>
        <li>🎬 <b>.mp4</b>, 🖼️ <b>.gif</b> — медіа-плеєр / зображення;</li>
        <li>📊 <b>.pptx</b>, 📃 <b>.docx</b> — текстовий вміст;</li>
        <li>📊 <b>.ppt</b>, 🔷 <b>.jar</b>, 🎞️ <b>.avi</b> — картка з можливістю
            відкрити файл у системі.</li>
      </ul>
      <p>Кнопка пошуку вгорі фільтрує файли за назвою.</p>
    </div>
    {help_html}
    """)


def wrap_doc(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
  :root {{
    --p-bg: #fdfdfd; --p-fg: #222; --p-h: #1a3a6b; --p-line: #b9c6da;
    --p-th: #e8eef8; --p-mdth: #ffe9c7; --p-code: #f0f2f6;
    --p-card: #fff; --p-note-fg: #8a5a00; --p-note-bg: #fff6e0;
    --p-hint: #777; --p-link: #0b5cad;
  }}
  html[data-theme="dark"] {{
    --p-bg: #14181f; --p-fg: #d7dde6; --p-h: #9db8e8; --p-line: #2c3547;
    --p-th: #232c3d; --p-mdth: #4a3a1e; --p-code: #232b3d;
    --p-card: #1c2230; --p-note-fg: #e8b64c; --p-note-bg: #2c2417;
    --p-hint: #9aa3b2; --p-link: #7db3ff;
  }}
  body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 24px;
         background: var(--p-bg); color: var(--p-fg); line-height: 1.5; }}
  h1, h2, h3 {{ color: var(--p-h); }}
  table {{ border-collapse: collapse; margin: 12px 0; width: 100%; }}
  th, td {{ border: 1px solid var(--p-line); padding: 6px 10px; text-align: left;
           font-size: 14px; }}
  th {{ background: var(--p-th); }}
  .md table th {{ background: var(--p-mdth); }}
  code, pre {{ background: var(--p-code); padding: 2px 5px; border-radius: 4px;
              font-family: Consolas, monospace; }}
  pre {{ padding: 12px; overflow-x: auto; }}
  .card {{ max-width: 720px; margin: 40px auto; background: var(--p-card);
          border: 1px solid var(--p-line); border-radius: 10px; padding: 28px;
          text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
  .card-icon {{ font-size: 56px; }}
  .meta {{ text-align: left; }}
  a {{ color: var(--p-link); }}
  .note {{ color: var(--p-note-fg); background: var(--p-note-bg); padding: 10px;
          border-radius: 6px; }}
  .btn {{ display: inline-block; background: #1a6bd6; color: #fff !important;
         padding: 10px 22px; border-radius: 6px; text-decoration: none;
         font-weight: 600; }}
  .btn:hover {{ background: #145bb5; }}
  .hint {{ color: var(--p-hint); font-size: 13px; }}
  .slide {{ border: 1px solid var(--p-line); border-radius: 8px; padding: 14px 18px;
           margin: 14px 0; background: var(--p-card); }}
  .slide h3 {{ margin-top: 0; }}
  .pics img {{ max-width: 46%; border: 1px solid #ccc; border-radius: 6px;
              margin: 6px; vertical-align: top; }}
  video {{ width: 100%; max-height: 78vh; background: #000; border-radius: 8px; }}
  .slideimg {{ width: 100%; border: 1px solid #cfd8e6; border-radius: 6px;
              box-shadow: 0 1px 4px rgba(0,0,0,.12); }}
  details {{ margin-top: 8px; }}
  details summary {{ cursor: pointer; color: var(--p-link); font-size: 13px; }}
  .stext {{ background: var(--p-code); padding: 8px 12px; border-radius: 6px;
           margin-top: 6px; }}
  blockquote {{ border-left: 4px solid #1a6bd6; margin: 10px 0;
               padding: 4px 14px; color: var(--p-fg); background: var(--p-th); }}
</style>
<script>
// Тема iframe — слідує за батьком (direct access, бо srcdoc = same origin)
(function () {{
  function apply(t) {{
    document.documentElement.setAttribute('data-theme', t === 'dark' ? 'dark' : 'light');
  }}
  // Спочатку — тема батьківського документа (пряме читання, бо same origin)
  try {{
    var p = window.parent;
    if (p && p !== window && p.document) {{
      var pt = p.document.documentElement.getAttribute('data-theme');
      if (pt === 'dark' || pt === 'light') {{ apply(pt); }}
    }}
  }} catch (e) {{}}
  // Потім — збережена тема в iframe (перевизначає батьківську)
  try {{
    var saved = localStorage.getItem('pv_preview_theme');
    if (saved === 'light' || saved === 'dark') {{ apply(saved); }}
  }} catch (e) {{}}
  // Фоллбек: system preference
  if (!document.documentElement.getAttribute('data-theme')) {{
    var s = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      ? 'dark' : 'light';
    apply(s);
  }}
  // Слухаємо зміну теми в батьківському документі
  try {{
    if (window.parent && window.parent !== window && window.parent.MUTATION_OBSERVER_SUPPORTED) {{
      // Батько надсилає подію при зміні теми
      window.addEventListener('message', function handler(ev) {{
        if (ev.data && ev.data.type === 'theme_change') {{
          apply(ev.data.theme);
        }}
      }});
    }}
  }} catch (e) {{}}
}})();
</script></head><body>{body}</body></html>"""


# ---------------------------------------------------------------- сканування

def build_tree(base: Path):
    """Повертає (дерево, dict прев'ю: relpath -> html)."""
    previews = {}

    def walk(current: Path):
        entries = []
        dirs, items = [], []
        for child in sorted(current.iterdir(),
                            key=lambda p: (p.is_file(), p.name.lower())):
            (dirs if child.is_dir() else items).append(child)
        for d in dirs:
            if d.name == "viewer_assets" \
                    or d.name.startswith(".") or d.name == "__pycache__" \
                    or d.name.startswith(TEMP_PREFIX):
                continue
            node = walk(d)
            if node["children"]:
                entries.append(node)
        for f in items:
            if f.name in EXCLUDE_FILES \
                    or f.name.startswith(EXCLUDE_PREFIXES) \
                    or f.name.startswith("~$") \
                    or f.name.startswith(TEMP_PREFIX):
                continue
            ext = f.suffix.lower()
            rel = f.relative_to(base).as_posix()
            size = f.stat().st_size
            mode = "src"      # iframe.src — pdf, mp4, gif, html тощо
            src_override: str | None = None
            try:
                if ext == ".md":
                    mode = "srcdoc"
                    previews[rel] = render_md(f)
                elif ext == ".pptx":
                    mode = "srcdoc"
                    previews[rel] = render_pptx(f)
                elif ext == ".docx":
                    mode = "srcdoc"
                    try:
                        previews[rel] = render_docx_html(f)
                    except (KeyError, ValueError, OSError,
                            zipfile.BadZipFile, ET.ParseError):
                        try:
                            previews[rel] = render_docx(f)
                        except (KeyError, ValueError, OSError,
                                zipfile.BadZipFile):
                            previews[rel] = info_card(
                                f, "Не вдалося прочитати документ.")
                    doc_pdf = export_docx_pdf(f)
                    if doc_pdf is not None:
                        pdf_url = quote(doc_pdf.relative_to(base).as_posix())
                        previews[rel] = previews[rel].replace(
                            "</head>",
                            ("<style>.docsw{padding:2px 0 8px}"
                             ".docsw .tgl{margin:0 6px 0 0;padding:4px 12px;"
                             "cursor:pointer}.docsw .tgl.on{background:#e8eef8}"
                             ".docsw .docpdf{display:none;width:100%;height:80vh;"
                             "border:1px solid #999}</style>"
                             '<script>document.querySelectorAll(".docsw").forEach('
                             "function(b){b.querySelectorAll('.tgl').forEach("
                             "function(t){t.addEventListener('click',function(){"
                             "b.querySelectorAll('.tgl').forEach(function(x){"
                             "x.classList.remove('on')});t.classList.add('on');"
                             "var p=b.querySelector('.docpdf');"
                             "var h=b.querySelector('.dv-html');"
                             "if(t.dataset.v==='pdf'){p.style.display='block';"
                             "h.style.display='none';}"
                             "else{p.style.display='none';h.style.display='block';}"
                             "});});});</script></head>"), 1)
                        previews[rel] = previews[rel].replace(
                            "<article",
                            (f'<div class="docsw">'
                             f'<button class="tgl on" type="button" data-v="html">'
                             f'📄 HTML</button>'
                             f'<button class="tgl" type="button" data-v="pdf">'
                             f'📕 PDF</button>'
                             f'<iframe class="docpdf" src="{pdf_url}"></iframe>'
                             f'<div class="dv-html"><article'), 1)
                        previews[rel] = previews[rel].replace(
                            "</article></body>",
                            "</article></div></div></body>", 1)
                elif ext == ".avi":
                    conv = convert_avi(f)
                    if conv is not None:
                        mode = "src"
                        src_override = conv.relative_to(base).as_posix()
                    else:
                        mode = "srcdoc"
                        previews[rel] = avi_video_card(f)
                elif ext == ".ppt":
                    mode = "srcdoc"
                    p_files = export_office_slides(f)
                    if p_files:
                        previews[rel] = wrap_doc(
                            f.name,
                            f'<article class="doc"><h2>{html.escape(f.name)}</h2>'
                            + render_slides_preview(p_files, []) + "</article>")
                    else:
                        previews[rel] = info_card(
                            f, "Старий формат PowerPoint (.ppt): текстовий "
                               "попередній перегляд недоступний. Відкрийте "
                               "файл у Microsoft PowerPoint.")
                elif ext == ".jar":
                    mode = "srcdoc"
                    previews[rel] = info_card(
                        f, "Java-аплікація. Браузери не запускають .jar зі "
                           "сторінки — відкривайте через Провідник "
                           "(потрібна встановлена Java).")
                elif ext == ".xlsx":
                    mode = "srcdoc"
                    try:
                        previews[rel] = render_xlsx(f)
                    except ImportError:          # немає openpyxl
                        previews[rel] = render_xlsx_stdlib(f)
                elif ext == ".csv":
                    mode = "srcdoc"
                    previews[rel] = render_csv(f)
                elif ext == ".xls":
                    mode = "srcdoc"
                    previews[rel] = info_card(
                        f, "Старий формат Excel (.xls): структура не "
                           "читається без Excel. Відкрийте файл у Excel "
                           "або перезбережіть як .xlsx — тоді тут буде "
                           "показано таблицю.")
            except Exception as e:
                mode = "srcdoc"
                previews[rel] = info_card(f, f"Не вдалося витягти вміст: {e}")
            if ext not in KNOWN_PREVIEW_EXTS and rel not in previews:
                mode = "srcdoc"
                previews[rel] = info_card(
                    f, f"Формат «{ext or 'без розширення'}» не має вбудованого "
                       f"перегляду. Натисніть «🔗 Відкрити окремо», щоб "
                       f"відкрити файл у системній програмі.")

            entries.append({
                "name": f.name, "rel": rel, "isDir": False,
                "ext": ext, "size": human_size(size), "mode": mode,
                "src": src_override or rel, "icon": icon_for(f.name),
            })
        return {"name": current.name, "isDir": True, "children": entries,
                "icon": "📂"}

    return walk(base), previews


# ---------------------------------------------------------------- HTML-шаблон

def make_html(tree: dict, previews: dict, total_files: int) -> str:
    tree_json = json.dumps(tree, ensure_ascii=False).replace("</", "<\\/")
    prev_json = json.dumps(previews, ensure_ascii=False).replace("</", "<\\/")
    welcome = json.dumps(welcome_doc(), ensure_ascii=False).replace("</", "<\\/")
    root_js = json.dumps(str(BASE), ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8">
<title>Viewer-for-School · 11-Д — Перегляд матеріалів</title>
<style>
  * {{ box-sizing: border-box; }}
  :root {{
    --bg: #f4f6fa; --fg: #222; --panel: #fff; --line: #d8dfe9;
    --hover: #eef3fb; --active: #d7e5fb; --head: #1a3a6b;
    --btn: #2c5aa0; --btn-h: #3a6db8; --muted: #8a94a6; --link: #1a6bd6;
    --card-bg: #fdfdfd; --code-bg: #f0f2f6; --tbl-h: #e8eef8;
  }}
  html[data-theme="dark"] {{
    --bg: #14181f; --fg: #d7dde6; --panel: #1c2230; --line: #2c3547;
    --hover: #232c3d; --active: #2b3a55; --head: #0f1c33;
    --btn: #2c5aa0; --btn-h: #3a6db8; --muted: #8a94a6; --link: #7db3ff;
    --card-bg: #1a2130; --code-bg: #232b3d; --tbl-h: #232c3d;
  }}
  html, body {{ height: 100%; margin: 0; font-family: 'Segoe UI', sans-serif;
              background: var(--bg); color: var(--fg); }}
  header {{ background: var(--head); color: #fff; padding: 10px 16px;
           display: flex; align-items: center; gap: 14px; }}
  header h1 {{ font-size: 16px; margin: 0; font-weight: 600; }}
  #search {{ flex: 1; max-width: 420px; padding: 7px 12px; border: none;
            border-radius: 6px; font-size: 14px; }}
  #count {{ font-size: 12px; opacity: .8; margin-left: auto; }}
  .actions {{ display: flex; gap: 8px; }}
  .actions button {{ background: var(--btn); color: #fff; border: none;
                    padding: 6px 12px; border-radius: 6px; cursor: pointer;
                    font-size: 13px; white-space: nowrap; }}
  .actions button:hover {{ background: var(--btn-h); }}
  .actions button.regen {{ background: #1f8a4c; }}
  .actions button.regen:hover {{ background: #26a35a; }}
  .actions button.regen.busy {{ background: #6f7d8c; cursor: progress; }}
  #regMsg {{ font-size: 12px; white-space: nowrap; opacity: .92; }}
  main {{ display: flex; height: calc(100% - 49px); }}
  #tree {{ width: 340px; min-width: 340px; overflow: auto; background: var(--panel);
          border-right: 1px solid var(--line); padding: 10px 6px 30px;
          font-size: 13.5px; flex: none; }}
  #split {{ width: 8px; cursor: col-resize; flex: none;
           background: var(--line); }}
  #split:hover, #split.drag {{ background: var(--btn); }}
  details {{ margin-left: 14px; }}
  #tree > details {{ margin-left: 0; }}
  summary {{ cursor: pointer; padding: 3px 6px; border-radius: 5px;
           user-select: none; white-space: nowrap; }}
  summary:hover {{ background: var(--hover); }}
  .file {{ display: flex; align-items: center; gap: 7px; padding: 4px 6px
         4px 26px; cursor: pointer; border-radius: 5px; white-space: nowrap;
         overflow: hidden; }}
  .file:hover {{ background: var(--hover); }}
  .file.active {{ background: var(--active); font-weight: 600; }}
  .fsize {{ margin-left: auto; font-size: 11px; color: var(--muted);
           padding-left: 8px; }}
  #viewerWrap {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
  #frameTitle {{ background: var(--panel); border-bottom: 1px solid var(--line);
               padding: 8px 16px; font-size: 13px; color: var(--fg);
               display: flex; align-items: center; }}
  #ftText {{ flex: 1; white-space: nowrap; overflow: hidden;
            text-overflow: ellipsis; }}
  #ftOpen {{ color: var(--link); text-decoration: none; font-weight: 600;
            white-space: nowrap; padding-left: 14px; }}
  #ftOpen:hover {{ text-decoration: underline; }}
  #viewer {{ flex: 1; border: none; width: 100%; background: var(--panel); }}
  .hidden {{ display: none !important; }}
  .empty {{ padding: 4px 6px 4px 26px; color: var(--muted); font-style: italic; }}
</style>
</head>
<body>
<header>
  <h1>📚 Viewer-for-School · Навчальні матеріали</h1>
  <input id="search" type="search" placeholder="Пошук файлу…">
  <span class="actions">
    <button id="btnExpand" type="button" title="Розгорнути всі папки">📂 Розгорнути все</button>
    <button id="btnCollapse" type="button" title="Згорнути всі папки">📁 Згорнути все</button>
    <button id="btnRegen" class="regen" type="button" title="Перезапустити генератор і оновити дерево файлів">🔄 Оновити файли</button>
    <button id="btnHelp" type="button" title="Опис програми">ℹ️ Опис</button>
    <button id="btnThemePreview" type="button" title="Тема в прев'ю: auto/light/dark">🎨 Тема в прев'ю</button>
    <button id="btnTheme" type="button" title="Світла / темна тема">🌙 Тема</button>
  </span>
  <span id="regMsg"></span>
  <span id="count"></span>
</header>
<main>
  <nav id="tree"></nav>
  <div id="split" title="Потягніть, щоб змінити ширину панелей"></div>
  <div id="viewerWrap">
    <div id="frameTitle"><span id="ftText">Оберіть файл ліворуч</span>
      <a id="ftOpen" class="hidden" target="_blank" rel="noopener">🔗 Відкрити окремо</a></div>
    <iframe id="viewer" name="viewer"></iframe>
  </div>
</main>
<script>
// ---------------------------------------- тема (ідентифікатор: data-theme на <html>)
(function initTheme() {{
  let saved = null;
  try {{ saved = localStorage.getItem('pv_theme'); }} catch (e) {{}}
  if (saved !== 'light' && saved !== 'dark') {{
    saved = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
      ? 'dark' : 'light';
  }}
  document.documentElement.setAttribute('data-theme', saved);
  document.getElementById('btnTheme').textContent =
    (saved === 'dark' ? '☀️' : '🌙') + ' Тема';
}})();
document.getElementById('btnTheme').addEventListener('click', () => {{
  const cur = document.documentElement.getAttribute('data-theme') === 'dark'
    ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', cur);
  try {{ localStorage.setItem('pv_theme', cur); }} catch (e) {{}}
  document.getElementById('btnTheme').textContent =
    (cur === 'dark' ? '☀️' : '🌙') + ' Тема';
  // Синхронізуємо тему iframe (для прев'ю файлів)
  syncIframeTheme();
  // Повідомляємо iframe про зміну теми
  try {{
    const iframe = document.getElementById('viewer');
    if (iframe && iframe.contentWindow) {{
      iframe.contentWindow.postMessage({{ type: 'theme_change', theme: cur }}, '*');
    }}
  }} catch (e) {{}}
}});

const TREE = {tree_json};
const PREVIEWS = {prev_json};
const TOTAL = {total_files};

const treeEl = document.getElementById('tree');
const frame = document.getElementById('viewer');
const titleEl = document.getElementById('frameTitle');
const searchEl = document.getElementById('search');
document.getElementById('count').textContent = TOTAL + ' файлів';

function openFile(node, el) {{
  document.querySelectorAll('.file.active')
          .forEach(e => e.classList.remove('active'));
  if (el) el.classList.add('active');
  document.getElementById('ftText').textContent = node.rel + '  ·  ' + node.size;
  const openEl = document.getElementById('ftOpen');
  openEl.href = encodeURI(node.mode === 'srcdoc' ? node.rel
                                                 : (node.src || node.rel));
  openEl.classList.remove('hidden');
  if (node.mode === 'srcdoc') {{
    frame.removeAttribute('src');
    frame.srcdoc = PREVIEWS[node.rel] || '<p>Немає прев’ю</p>';
  }} else {{
    frame.removeAttribute('srcdoc');
    frame.src = encodeURI(node.src || node.rel);   // pdf / mp4 / gif / html / avi→mp4
  }}
}}

function build(node, parent) {{
  if (node.isDir) {{
    const det = document.createElement('details');
    det.open = true;
    det._node = node;
    const sum = document.createElement('summary');
    sum.textContent = '📁 ' + node.name;
    det.appendChild(sum);
    if (node.children.length === 0) {{
      const e = document.createElement('div');
      e.className = 'empty';
      e.textContent = '(порожня папка)';
      det.appendChild(e);
    }}
    node.children.forEach(ch => build(ch, det));
    parent.appendChild(det);
  }} else {{
    const div = document.createElement('div');
    div.className = 'file';
    div._node = node;
    div.innerHTML = '<span></span><span class="nm"></span>' +
                    '<span class="fsize"></span>';
    div.children[0].textContent = node.icon;
    div.querySelector('.nm').textContent = node.name;
    div.querySelector('.fsize').textContent = node.size;
    div.title = node.rel;
    div.addEventListener('click', () => openFile(node, div));
    parent.appendChild(div);
  }}
}}

function filter(q) {{
  q = q.toLowerCase().trim();
  const details = treeEl.querySelectorAll('details');
  const files = treeEl.querySelectorAll('.file');
  if (!q) {{
    files.forEach(f => f.classList.remove('hidden'));
    details.forEach(d => {{ d.classList.remove('hidden'); d.open = true; }});
    return;
  }}
  files.forEach(f => f.classList.toggle(
      'hidden', !f._node.name.toLowerCase().includes(q)));
  details.forEach(d => {{
    const has = Array.from(d.querySelectorAll('.file'))
                     .some(f => !f.classList.contains('hidden'));
    d.classList.toggle('hidden', !has);
    if (has) d.open = true;
  }});
}}

build(TREE, treeEl);
searchEl.addEventListener('input', e => filter(e.target.value));
document.getElementById('btnExpand').addEventListener('click', () => {{
  treeEl.querySelectorAll('details').forEach(d => {{ d.open = true; }});
}});
document.getElementById('btnCollapse').addEventListener('click', () => {{
  treeEl.querySelectorAll('details').forEach(d => {{ d.open = false; }});
}});

// ---------------------------------------- розсувний розділювач панелей
const splitEl = document.getElementById('split');
try {{
  const saved = parseInt(localStorage.getItem('pv_tree_w') || '', 10);
  if (saved >= 200 && saved <= 700) treeEl.style.width = saved + 'px';
}} catch (e) {{ /* приватний режим — лишаємо 340px */ }}
splitEl.addEventListener('pointerdown', (e) => {{
  e.preventDefault();
  splitEl.classList.add('drag');
  splitEl.setPointerCapture(e.pointerId);
  const startX = e.clientX;
  const startW = treeEl.getBoundingClientRect().width;
  const move = (ev) => {{
    const w = Math.max(200, Math.min(700, Math.round(startW + ev.clientX - startX)));
    treeEl.style.width = w + 'px';
  }};
  const up = (ev) => {{
    const w = Math.max(200, Math.min(700, Math.round(startW + ev.clientX - startX)));
    try {{ localStorage.setItem('pv_tree_w', String(w)); }} catch (err) {{}}
    splitEl.classList.remove('drag');
    splitEl.removeEventListener('pointermove', move);
    splitEl.removeEventListener('pointerup', up);
    splitEl.removeEventListener('pointercancel', up);
  }};
  splitEl.addEventListener('pointermove', move);
  splitEl.addEventListener('pointerup', up);
  splitEl.addEventListener('pointercancel', up);
}});

// ---------------------------- початкова сторінка (вона ж — сторінка опису)
const WELCOME_HTML = {welcome};
const PV_ROOT = {root_js};

// ---------------------------------------- «Оновити файли» (перезапуск генератора)
const regBtn = document.getElementById('btnRegen');
const regMsg = document.getElementById('regMsg');
const PORT_HINTS = [8321, 8322, 8323, 8324, 8325, 8326];
let SERVER_BASE = null;      // '' — той самий сервер (http), null — не знайдено

function setReg(busy, text) {{
  regBtn.classList.toggle('busy', busy);
  regBtn.disabled = busy;
  regMsg.textContent = text || '';
}}

async function findServer() {{
  if (location.protocol === 'http:' || location.protocol === 'https:') {{
    return '';               // сторінку віддає сам viewer_server
  }}
  for (const p of PORT_HINTS) {{
    const base = 'http://127.0.0.1:' + p;
    try {{
      const r = await fetch(base + '/api/status', {{ cache: 'no-store' }});
      if (r.ok) {{
        const d = await r.json();
        // беремо лише «свій» сервер — той, що роздає саму цю теку
        if (d && d.ok &&
            (!d.root || d.root.toLowerCase() === PV_ROOT.toLowerCase())) return base;
      }}
    }} catch (e) {{ /* порт вільний — пробуємо наступний */ }}
  }}
  return null;
}}

async function regen() {{
  setReg(true, '⏳ оновлення…');
  try {{
    if (SERVER_BASE === null) SERVER_BASE = await findServer();
    if (SERVER_BASE === null) {{
      setReg(false, '⚠ сервер не запущено — відкрийте через start_viewer.bat');
      return;
    }}
    const r = await fetch(SERVER_BASE + '/api/regen', {{ cache: 'no-store' }});
    const d = await r.json();
    if (d && d.ok) {{
      const secs = Math.round((d.ms || 0) / 100) / 10;
      setReg(true, '✅ оновлено за ' + secs + ' с — перезавантаження…');
      setTimeout(() => location.reload(), 700);
    }} else {{
      const err = (d && (d.error || d.stderrTail)) || 'невідома помилка';
      setReg(false, '❌ помилка: ' + err);
    }}
  }} catch (e) {{
    setReg(false, '❌ не вдалося зв’язатися із сервером: ' + e);
  }}
}}

regBtn.addEventListener('click', regen);
(async () => {{
  SERVER_BASE = await findServer();
  setReg(false, SERVER_BASE === null
      ? '⚪ офлайн: відкрийте через start_viewer.bat'
      : '🟢 сервер активний');
}})();

frame.srcdoc = WELCOME_HTML;

// Синхронізація теми iframe з батьком (після завантаження iframe)
function syncIframeTheme() {{
  try {{
    const iframe = document.getElementById('viewer');
    if (iframe && iframe.contentDocument) {{
      const parentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      iframe.contentDocument.documentElement.setAttribute('data-theme', parentTheme);
    }}
  }} catch (e) {{ /* ігноруємо */ }}
}}
// Відповідаємо на запит теми від iframe
window.addEventListener('message', function(ev) {{
  if (ev.data && ev.data.type === 'get_theme') {{
    ev.source.postMessage({{ type: 'theme', theme: document.documentElement.getAttribute('data-theme') || 'light' }}, ev.origin);
  }}
}});
// Чекаємо поки iframe завантажиться
document.getElementById('viewer').addEventListener('load', syncIframeTheme);
// Дубль: через 100ms (на випадок якщо load вже спрацював)
setTimeout(syncIframeTheme, 100);
// Позначаємо, що батьківський документ підтримує прямий доступ до теми
document.MUTATION_OBSERVER_SUPPORTED = true;

// ---------------------------------------- кнопки «Опис» і «Тема в прев'ю»
document.getElementById('btnHelp').addEventListener('click', () => {{
  // Кнопка «ℹ️ Опис» показує початкову сторінку (окремих сторінок опису немає)
  frame.srcdoc = WELCOME_HTML;
  document.getElementById('ftText').textContent = '📖 Опис програми';
  document.getElementById('ftOpen').classList.add('hidden');
  setTimeout(() => syncIframeTheme(), 50);   // синхронізуємо тему iframe
}});

// Тема в прев'ю: цикл auto → light → dark → auto
// ЗМІНЮЄ ТІЛЬКИ тему в iframe (прев'ю файлів), НЕ головну сторінку
function getPreviewTheme() {{
  try {{ return localStorage.getItem('pv_preview_theme') || 'auto'; }} catch (e) {{ return 'auto'; }}
}}
function setPreviewTheme(val) {{
  try {{ localStorage.setItem('pv_preview_theme', val); }} catch (e) {{}}
}}
let previewCycle = ['auto','light','dark'];
function applyPreviewThemeToIframe() {{
  let mode = getPreviewTheme();
  try {{
    const iframe = document.getElementById('viewer');
    if (iframe && iframe.contentDocument) {{
      if (mode === 'auto') {{
        // Слідує за темою батька
        const parentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        iframe.contentDocument.documentElement.setAttribute('data-theme', parentTheme);
      }} else {{
        // Фіксована тема для iframe
        iframe.contentDocument.documentElement.setAttribute('data-theme', mode);
      }}
    }}
  }} catch (e) {{}}
}}
document.getElementById('btnThemePreview').addEventListener('click', () => {{
  let cur = getPreviewTheme();
  let idx = previewCycle.indexOf(cur);
  let next = previewCycle[(idx+1)%3];
  setPreviewTheme(next);
  // Застосовуємо тему ТІЛЬКО до iframe (прев'ю файлів)
  applyPreviewThemeToIframe();
  document.getElementById('btnThemePreview').textContent = '🎨 ' + getPreviewTheme();
}});

// Ініціалізація: якщо pv_preview_theme не збережений — встановити 'auto'
(function initPreviewTheme() {{
  try {{
    if (!localStorage.getItem('pv_preview_theme')) {{
      localStorage.setItem('pv_preview_theme', 'auto');
    }}
  }} catch (e) {{}}
  // Оновити iframe з поточною темою
  applyPreviewThemeToIframe();
  // Встановити текст кнопки
  document.getElementById('btnThemePreview').textContent = '🎨 ' + getPreviewTheme();
}})();

// Коли змінюється глобальна тема (кнопка 🌙) — оновлюємо iframe якщо в режимі auto
window.addEventListener('storage', (ev) => {{
  if (ev.key === 'pv_theme') {{
    // Глобальна тема змінилась — оновлюємо iframe якщо в режимі auto
    let mode = getPreviewTheme();
    if (mode === 'auto') {{
      applyPreviewThemeToIframe();
    }}
  }}
  // pv_preview_theme змінився — оновлюємо iframe
  if (ev.key === 'pv_preview_theme') {{
    applyPreviewThemeToIframe();
  }}
}});
</script>
</body>
</html>"""


# ---------------------------------------------------------------- main

def main() -> int:
    if not BASE.is_dir():
        print(f"ПОМИЛКА: папку не знайдено: {BASE}", file=sys.stderr)
        return 1

    print(f"Сканування: {BASE} ...", flush=True)
    prewarm_office_exports(BASE)
    if "--prewarm" in sys.argv:
        return 0
    tree, previews = build_tree(BASE)

    def count_files(node):
        if not node["isDir"]:
            return 1
        return sum(count_files(c) for c in node["children"])

    total = count_files(tree)
    print(f"Знайдено файлів: {total}; прев’ю згенеровано: {len(previews)}",
          flush=True)
    out = BASE / OUT_NAME
    html_text = make_html(tree, previews, total)
    tmp = BASE / (OUT_NAME + ".tmp")     # атомарний запис: браузер ніколи
    tmp.write_text(html_text, encoding="utf-8")   # не побачить обірваної
    os.replace(tmp, out)                          # сторінки під час regen
    print(f"Готово: {out} ({human_size(out.stat().st_size)})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
