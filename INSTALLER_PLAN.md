# План завершення інсталятора — Viewer-for-School

Оновлено: 24.09.2026. Це **єдине джерело** плану інсталятора (попередні варіанти
плану видалено). Продукт: **Viewer-for-School**; publisher і copyright:
`FileViewer-for-students-and-teachers`.

## 1. Мета

Portable-інсталятор Inno Setup, який:

1. встановлює додаток у **вибрану теку** — корінь навчальної теки з матеріалами;
2. створює ярлики «📚 Viewer-for-School» і «⚙️ Згенерувати для теки…»;
3. ставить потрібне ПЗ: Python (за згодою), pip-пакети; **детектує** Office і ffmpeg;
4. несе все необхідне для роботи: усе інше (`viewer.html`, `viewer_assets/`)
   **генерується на місці** при запуску;
5. компілюється однією командою для нових версій.

## 2. Зафіксовані рішення

| № | Рішення |
|---|---|
| 1 | Модель: portable, інсталяція у вибрану теку (не `Program Files`) |
| 2 | `BASE` без хардкоду: `argv[1]`/`--root` → тека скриптів → cwd |
| 3 | `viewer.html` не пакуємо — генерується у теці встановлення |
| 4 | `viewer_assets/` не пакуємо — генерується (Office COM / ffmpeg) |
| 5 | Ярлик «Згенерувати для теки…» приймає теку як аргумент |
| 6 | Деінсталяція: лише скрипти/ярлики; матеріали, `viewer.html`, `viewer_assets/` — не чіпаємо |
| 7 | Python: автозавантаження з python.org (з підтвердженням), фолбек — winget |
| 8 | pip-пакети: `python -m pip install --user -r requirements.txt` |
| 9 | Office — лише детекція + попередження (авто-установка неможлива, ліцензія) |
| 10 | ffmpeg не пакуємо: опційно winget `Gyan.FFmpeg.Essentials`, інакше попередження + посилання |
| 11 | Версія: `VERSION` вручну + `/DAppVersion=` (semver), стартова — `1.1.0` |
| 12 | Галочка першої генерації — увімкнена за замовчуванням (знімається) |
| 13 | Іконки: `installer/app.ico`, `wizard.png` (240×459), `wizard-small.png` (150×57) |
| 14 | Ліцензія: канонічний MIT, copyright `FileViewer-for-students-and-teachers` |
| 15 | Назва продукту `Viewer-for-School` — у всіх user-visible місцях (технічні імена файлів не змінюємо) |
| 16 | Кнопка «ℹ️ Опис» веде на **початкову сторінку** (окремих сторінок опису немає) |
| 17 | Коміт — після перевірки робочого інсталятора; push — окремо |

## 3. Артефакти

| Пакує інсталятор | Генерується на місці | Не пакуємо |
|---|---|---|
| `generate_viewer.py`, `viewer_server.py`, `viewer_probe.py`, `start_viewer.bat`, `generate_for.bat`, `install_deps.py`, `viewer_help.md`, `requirements.txt`, `LICENSE.txt` | `viewer.html`, `viewer_assets/`, `viewer_server.port` | матеріали, `progect-viewer-school/`, `installer/Output/`, `__pycache__/`, `viewer_assets/jobs.tsv` |

## 4. Ітерація 1 — статус

| # | Крок | Файли | Статус |
|---|---|---|---|
| 0 | Прибрати хардкод шляху (`resolve_base()`) + `--root` у сервері | `generate_viewer.py`, `viewer_server.py` | ✅ |
| 0-I | Кнопка «ℹ️ Опис» → початкова сторінка (`WELCOME_HTML`), без окремих сторінок | `generate_viewer.py` | ✅ |
| 0-B | Бренд `Viewer-for-School` у UI/док/ліцензії | `generate_viewer.py`, `viewer_server.py`, `README.md`, `viewer_help.md`, `LICENSE.txt` | ✅ |
| 1 | Залежності: `requirements.txt` + `install_deps.py` (єдина точка) | нові файли, `start_viewer.bat` | ✅ |
| 2 | Прибирання: новий `LICENSE.txt`, видалення `installer/__init__.py`, `.gitignore` | `LICENSE.txt`, `.gitignore` | ✅ |
| 3a | `generate_for.bat` (аргумент або діалог вибору теки) | новий файл | ✅ |
| 3b | Скрипти інсталятора: `viewer_setup.iss`, `requirements_note.txt`, `make_assets.py` + іконки | `installer/` | ✅ |
| 6 | Компіляція: `winget install JRSoftware.InnoSetup` → `ISCC.exe` → `.exe` | `installer/Output/` | ✅ |
| 6-T | Тести: тиха інсталяція, ярлики, мова, ліцензія, генерація в теці встановлення, деінсталяція | — | ✅ |

> **Додатково виявлено й виправлено при тестах (24.09):** кирилиця в `.bat`
> ламала cmd (кодування) — обидва батники переведено в **чистий ASCII**
> (український текст діалогу вибору теки передається через PowerShell
> `-EncodedCommand`, UTF-16LE+base64); завершальний `\` у `%~dp0` перетворював
> аргумент `--root "…\"` на шлях із зайвою лапкою — додано обрізання
> бекслеша в обох батниках і `rstrip('"')` у Python; `stderr` усіх скриптів
> переведено в UTF-8 (щоб помилки не «кракозябрило»).

## 5. Ітерація 2 — статус

| # | Крок | Файли | Статус |
|---|---|---|---|
| 4a | Детекція Python (реєстр HKLM+HKCU по підключах, PATH без WindowsApps-stub) | `installer/viewer_setup.iss` `[Code]` | ✅ |
| 4b | Авто-установка Python: `DownloadTemporaryFile` (python.org 3.14.7, SHA-256) → `/quiet InstallAllUsers=0 PrependPath=1 …`; фолбек — `winget install Python.Python.3.14`; НІ → python.org, СКАС → без Python; у тихому режимі — без діалогів | `[Code]` | ✅ |
| 4c | Детекція Office/ffmpeg + попередження; пропозиція `Gyan.FFmpeg.Essentials` (winget) | `[Code]`, `install_deps.py` | ✅ |
| 4d | Захист теки: заборона `{win}`/Program Files, перевірка права запису (`MsgText` для `%n`) | `[Code]` | ✅ |
| 5 | Версіонування: `VERSION` + `installer/build.ps1` (читає VERSION, `/DAppVersion=`, UTF-8 BOM) | нові файли | ✅ |
| 7 | Повний цикл валідації (10 сценаріїв, див. §6) | — | ✅ (автоматично + ручна перевірка користувача) |
| 8 | Документація: `README.md`, `viewer_help.md`, `installer/README.md`, цей файл | док | ✅ |

## 6. Валідація (обов'язкова перед «готово»)

1. `ISCC.exe installer\viewer_setup.iss` → 0 помилок; `installer\Output\Viewer-for-School-Setup-<ver>.exe` існує.
2. Тиха інсталяція: `…Setup.exe /SILENT /DIR="…\TestInstall" /LOG="…\inst.log"`.
3. Візард: українська мова, сторінка ліцензії показує MIT (а не README), є інструкція «встановлювати в корінь навчальної теки».
4. Ярлики: у меню Пуск «📚 Viewer-for-School» та «⚙️ Згенерувати для теки…»; desktop — за галочкою.
5. Запуск з тестової теки → `viewer.html` і `viewer_assets/` з'являються **у теці встановлення**; `/api/status` → 200.
6. «⚙️ Згенерувати для теки…» — окрема тека (аргумент і діалог вибору).
7. Кнопка «🔄 Оновити файли» працює лише зі «своїм» сервером (перевірка `root`).
8. Сценарії без Python / без `markdown` / без Office → зрозумілі повідомлення, без крашів.
9. Деінсталяція → скрипти й ярлики прибрані; матеріали, `viewer.html`, `viewer_assets/` збережені.
10. Запуск у `J:\328_11-D\I semestr` без регресій (той самий набір файлів у дереві).

**Результати валідації від 24.09.2026:**

| # | Сценарій | Результат |
|---|----------|-----------|
| 1 | `build.ps1` → ISCC 0 помилок → `installer\Output\Viewer-for-School-Setup-1.1.0.exe` | ✅ |
| 2 | Тиха інсталяція `/SILENT /DIR=… /LOG=… /TASKS=deps,firstgen,desktopicon` → exit 0, лог без помилок | ✅ |
| 3 | Візард: мова, ліцензія MIT, підказка «встановити в корінь теки» | ✅ ручна перевірка користувачем (24.09.2026): «встановлення працює» |
| 4 | Ярлики: 3 у меню Пуск (українські назви) + desktop за галочкою | ✅ |
| 5 | Запуск із теки встановлення: `viewer.html` на місці, `/api/status` → 200, `root` = тека встановлення | ✅ |
| 6 | `generate_for.bat "<тестова тека>"` → `viewer.html` з правильним `PV_ROOT`; діалог вибору — парсер `-EncodedCommand` OK, діалог — ручна перевірка | ✅ |
| 7 | `/api/regen` → `ok:true` (207 мс, код 0); клієнтська перевірка `root` перед регенерацією | ✅ |
| 8 | Сценарії «без Python / без markdown / без Office» | ⚠️ частково: код і тексти повідомлень перевірено компіляцією; повний прогін — лише на машині без цих компонентів |
| 9 | Деінсталяція `/SILENT` → скрипти/ярлики/реєстр чисті; `viewer.html` і матеріали — на місці | ✅ |
| 10 | Запуск у `J:\328_11-D\I semestr` без регресій (456 файлів, 74 прев'ю) | ✅ |

**Ручна перевірка інсталятора — користувач, 24.09.2026:** ✅ «перевірив
інсталяцію вручну, все працює» — встановлення через візард, ярлики, генерація
і перегляд підтверджені на практиці; на підставі цього закрито сценарії 3 і 6
(діалог вибору теки).

**Підсумок Iteration 1 + Iteration 2 (24.09.2026):** усі кроки §4–§5 ✅;
валідація §6 пройдена (9 із 10 — автоматично/ручно, сценарій 8 — неповністю,
див. вище). Артефакт збірки: `installer\Output\Viewer-for-School-Setup-1.1.0.exe`.
**Статус: готово до коміту** (умова рішення №17 — робочий інсталятор
перевірено); коміт/пуш — окремим кроком.

## 7. Відомі проблеми, які виправляє цей план (з доказами)

| Проблема | Доказ |
|---|---|
| Застосунок не переносний — шлях зашитий у код | `generate_viewer.py:27` (`BASE = Path(r"J:\…")`) |
| Сервер і генератор могли писати в різні теки | `viewer_server.py:31` (`BASE = __file__.parent`) при хардкоді генератора |
| `.iss` не компілювався: відсутні `LICENSE.txt`/`wizard.bmp` за відносними шляхами, застарілі директиви (`InfoBeforeText`, `WizardSize`, `SolidCompress`, `DialogColor`), неіснуючі типи/сигнатури в `[Code]` (`TExecResult`, `WizardForm.WizardImages`, `OpenKeyReadOnly(key, True)`), ризик вічного циклу в `FindPythonExe` | `installer/viewer_setup.iss` (старий, 52 рядки) |
| pip-команда не ставила обов'язковий `markdown` і ставила невживаний `Pillow` | старий `.iss:42` vs `generate_viewer.py:19` |
| `start_viewer.bat` міг завершуватися з кодом 1 через `& exit /b 1` усередині `for ( )` | `start_viewer.bat:4–6` (переписано) |
| Кнопка «ℹ️ Опис» дублювала початкову сторінку окремим HTML | `generate_viewer.py:1692–1723` |
| `installer/__init__.py` — невалідний Python (`` `n `` замість переводів рядків) | `ast.parse` → SyntaxError (файл видалено) |
| `LICENSE.txt` був копією `installer/README.md` зі сміттям | порівняння байтів (файл переписано) |
