# Інсталятор Viewer-for-School

Portable-інсталятор на **Inno Setup 6**: ставить додаток у вибрану теку
(корінь навчальної теки з матеріалами), створює ярлики, за потреби доставляє
Python і pip-залежності. `viewer.html` і `viewer_assets/` **не пакуються** —
вони генеруються на місці при запуску.

## Збірка

```powershell
# Варіант 1 (рекомендовано): версія береться з файлу VERSION у корені
powershell -ExecutionPolicy Bypass -File installer\build.ps1

# Варіант 2: вручну
ISCC.exe /DAppVersion=1.1.0 installer\viewer_setup.iss
```

Результат: `installer\Output\Viewer-for-School-Setup-<версія>.exe`.

Потрібен Inno Setup 6 (`winget install JRSoftware.InnoSetup`).
`build.ps1` шукає `ISCC.exe` у Program Files / Program Files (x86) / LocalAppData
і в PATH; працює і в Windows PowerShell 5.1, і в PowerShell 7 (файл у UTF-8 з BOM).

**Версіонування:** єдине джерело правди — файл `VERSION` у корені репозиторію
(формат `X.Y.Z`). Для нової версії: оновіть `VERSION` → запустіть `build.ps1`.

## Що робить `viewer_setup.iss`

| Крок | Поведінка |
|------|-----------|
| Мова | українська / english (за мовою ОС) |
| Ліцензія | `LICENSE.txt` (MIT) + `requirements_note.txt` перед вибором теки |
| Вибір теки | підказка «встановити в КОРІНЬ навчальної теки»; заборона `{win}`/Program Files; перевірка права запису |
| Python | реєстр HKLM+HKCU (`SOFTWARE\Python\PythonCore`, ≥ 3.8) → PATH (без WindowsApps-заглушки). Немає → діалог: **ТА** — завантаження `python.org` з перевіркою SHA-256 (фолбек — `winget install Python.Python.3.14`), **НІ** — відкрити сторінку завантаження, **СКАС** — продовжити без Python |
| Залежності (завдання) | `install_deps.py` → `pip install --user -r requirements.txt` |
| Перша генерація (завдання) | `generate_viewer.py "<тека>"` одразу після встановлення |
| Office | детект COM-ключів Word/PowerPoint → попередження (без авто-установки: ліцензія) |
| ffmpeg | детект `ffmpeg.exe` у PATH → пропозиція `winget install Gyan.FFmpeg.Essentials` (згата Так/Ні) |
| Ярлики | «📚 Viewer-for-School», «⚙️ Згенерувати для теки…», «Видалити…»; desktop — за галочкою |
| Деінсталяція | прибирає скрипти, ярлики, `viewer_server.*`; **матеріали, `viewer.html`, `viewer_assets/` — не чіпає** |

Тихі режими: `/SILENT`, `/VERYSILENT`, `/DIR=...`, `/LOG=...`,
`/TASKS=deps,firstgen,desktopicon`, `/CURRENTUSER` або `/ALLUSERS`
(за наявності `PrivilegesRequiredOverridesAllowed=dialog`).
У тихому режимі діалоги Python/Office/ffmpeg не показуються (лише запис у лог).

## Що пакується / що ні

| Пакується | Генерується на місці | Не пакується |
|-----------|----------------------|--------------|
| `generate_viewer.py`, `viewer_server.py`, `viewer_probe.py`, `install_deps.py`, `start_viewer.bat`, `generate_for.bat`, `requirements.txt`, `viewer_help.md`, `LICENSE.txt`, `VERSION`, `app.ico` | `viewer.html`, `viewer_assets/`, `viewer_server.port` | матеріали, `progect-viewer-school/`, `installer/Output/`, `__pycache__/`, `viewer_assets/jobs.tsv` |

## Ресурси

- `make_assets.py` — генерує `app.ico`, `wizard.png` (240×459), `wizard-small.png` (150×57)
  (потребує Pillow; у репозиторії вже згенеровані — перегенеровувати лише за потреби).
- SHA-256 інсталтора Python у `[Code]` (`PythonDlSha256`) звірено з таблицею
  на python.org і winget-мейнфестом `Python.Python.3.14` — **оновлювати разом
  із `PythonDlUrl`/`WingetPythonId`** при переході на нову версію Python.

## Чек-лист валідації

1. `build.ps1` → 0 помилок, `.exe` у `Output\`.
2. Тиха інсталяція: `/SILENT /DIR=<тест> /LOG=<лог> /TASKS=deps,firstgen,desktopicon` → exit 0.
3. У теці є скрипти + `viewer.html`; ярлики в меню Пуск (1 користувач або спільне) та на робочому столі.
4. Запуск `start_viewer.bat` → `/api/status` → 200, `root` = тека встановлення.
5. `/api/regen` → `ok:true`, `viewer.html` перегенеровано.
6. `generate_for.bat "<тестова тека>"` → `viewer.html` у ній.
7. Деінсталяція `/SILENT` → скрипти й ярлики зникли; `viewer.html`/матеріали — на місці.
8. Запуск у репозиторії без регресій (дерево файлів те саме).
