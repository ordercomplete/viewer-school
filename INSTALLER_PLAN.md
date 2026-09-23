# План реалізації: інсталятор Inno Setup для viewer

**Ціль:** створити інсталятор `installer/viewer_setup.iss`, який:
1. Перевіряє наявність Python 3.8+.
2. Пропонує згоду на правила та умови використання.
3. Попереджає про необхідність встановлення додаткового ПЗ (openpyxl, python-pptx, Pillow).
4. Встановлює залежності через pip після згоди.
5. Копіює файли програми у поточну папку з навчальним матеріалом.
6. Створює ярлик «📚 Перегляд матеріалів» і кнопку генерації.

## Кроки виконання:

### Крок 1 — створити `installer/README.md`

Опис інструкції як зібрати `.exe`.

### Крок 2 — створити `installer/viewer_setup.iss` (скрипт Inno Setup)

**Логіка:**
- `[Setup]` — параметри базові.
- `[LangOptions]` та `[CustomMessages]` для української мови.
- `[Files]` — копіювання:
  - `generate_viewer.py`
  - `viewer_server.py`
  - `viewer_probe.py`
  - `start_viewer.bat`
  - `viewer.html` (шаблон)
  - `viewer_help.md`
  - `installer/__init__.py`
  - папка `viewer_assets/` (якщо є)
- `[Icons]`:
  - «📚 Перегляд матеріалів» → `start_viewer.bat`
  - «Згенерувати для теки…» → `cmd /k generate_viewer.py "%~dp0"`
- `[Run]` — перевірка Python та встановлення залежностей:
  ```iss
  Filename: "{cmd}"; Parameters: "/C python --version"; Flags: runhidden; Check: not IsPythonInstalled
  Filename: "{cmd}"; Parameters: "/C pip install openpyxl python-pptx Pillow --quiet"; 
          StatusMsg: "Встановлюються залежності..."; Flags: runhidden waituntilterminated
  ```
- `[CustomMessages]` — текст умов використання:
  ```iss
  LicenseDescription=Ця програма призначена для дистанційного заочного навчання старших класів середньої школи. Використовується безкоштовно як є, без претензій.
  InfoBeforeText=- Python 3.8+\n- openpyxl\n- python-pptx\n- Pillow (PIL)\n\nЯкщо компоненти відсутні, інсталятор спробує їх встановити через pip.
  ```

### Крок 3 — створити `installer/__init__.py`

Порожній файл або з версією:
```python
"""Installer package for viewer."""
__version__ = "1.0"
```

### Крок 4 — перевірити, що тема в XLSX не змінює фон таблиці

Переглянути `render_xlsx` у файлі `generate_viewer.py`:
- Рядки ~990–1116.
- Переконаємось, що немає блоків типу `<style>html[data-theme="dark"] { ... }</style>` для таблиць.
- Фон має бути завжди світлим.

### Крок 5 — запустити генерацію + перевірити працездатність (unit-тест на рівні запуску)

**Unit-тест:**
```bash
# Запуск
python generate_viewer.py

# Перевірка: у viewer.html є:
# - <button id="btnHelp">ℹ️ Опис</button>
# - <button id="btnThemePreview">🎨 Тема в прев'ю</button>
# - iframe #helpFrame з HELP_HTML
# - JS-скрипт, що обробляє кліки

# unit-test скрипт:
import re, sys; from pathlib import Path
html = Path("viewer.html").read_text(encoding="utf-8")
assert '<button id="btnHelp">ℹ️ Опис</button>' in html or 'ℹ️ Опис' in html
assert '🎨 Тема в прев\'ю' in html
import re; assert re.search(r'<div id="helpFrame"', html)
assert 'localStorage.getItem(\'pv_preview_theme\')' in html
```

### Крок 6 — очистити тимчасові артефакти

Видалити:
- `_tx_*.py` (тестові скрипти)
- `_sv_*.py`
- `_sv_*.html`
- `_sv_*.png`
- `_tx_body.xml`
- `_tx5_out.txt`
- `_tx5.png`
- `_tx5.py`

Залишити:
- `viewer_probe.py`
- `_replace_proj_path.py` (якщо службовий)
- `_check_renaming.py`

Команда:
```powershell
del /f "_tx_*.py" "_sv_*.py" "_sv_*.html" "_sv_*.png" "_tx_body.xml" "_tx5_out.txt" "_tx5.png" "_tx5.py" 2>$null
```

---

## Впровадження UI-елементів у `generate_viewer.py` (Крок 1A–1E)

### Крок 1A — зчитати `viewer_help.md` і перетворити на HTML

У функції `welcome_doc()` або новій функції, що викликається при генерації:
```python
HELP_MD_PATH = BASE / "viewer_help.md"
HELP_HTML = ""
if HELP_MD_PATH.exists():
    try:
        md_text = HELP_MD_PATH.read_text(encoding="utf-8")
        HELP_HTML = _md_to_html(md_text)
    except Exception:
        pass
```

### Крок 1B — додати кнопки в `wrap_doc()` або там, де збирається шапка HTML

У тілі `<body>` додати:
```html
<header style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
  <button id="btnHelp" title="ℹ️ Опис">ℹ️ Опис</button>
  <button id="btnThemePreview" title="🎨 Тема в прев'ю">🎨 Тема в прев'ю</button>
  <button id="btnRefresh" title="🔄 Оновити файли">🔄 Оновити файли</button>
  <button id="btnTheme" title="Тема">🌙 Тема</button>
</header>
```

### Крок 1C — додати прихований `<div>` для опису (фрейм)
```html
<div id="helpFrame" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;">
  <div style="background:#fff;padding:24px;height:100%;overflow:auto;">
    <button onclick="document.getElementById('helpFrame').style.display='none'">❌ Закрити</button>
    <!-- вставити HELP_HTML сюди -->
  </div>
</div>
```

### Крок 1D — додати JS для кнопок

В кінці HTML (перед `</body>`):
```javascript
// Кнопка ℹ️ Опис
document.getElementById('btnHelp').onclick = function() {
  document.getElementById('helpFrame').style.display = 'block';
};

// Кнопка 🎨 Тема в прев'ю — цикл auto/light/dark
function getPreviewTheme() {
  return localStorage.getItem('pv_preview_theme') || 'auto';
}
function setPreviewTheme(val) {
  localStorage.setItem('pv_preview_theme', val);
}
let previewCycle = ['auto','light','dark'];
document.getElementById('btnThemePreview').onclick = function() {
  let cur = getPreviewTheme();
  let idx = previewCycle.indexOf(cur);
  setPreviewTheme(previewCycle[(idx+1)%3]);
  updatePreviewFrameTheme();
};

// Синхронізація: auto → слідкує за pv_theme, light/dark → фіксовано.
function applyThemeToPreview() {
  let mode = getPreviewTheme();
  if (mode === 'auto') {
    // Слідкує за глобальною темою pv_theme
    let globalTheme = localStorage.getItem('pv_theme') || 'light';
    document.documentElement.setAttribute('data-theme', globalTheme);
  } else {
    document.documentElement.setAttribute('data-theme', mode);
  }
}

// Запуск при завантаженні
document.addEventListener('DOMContentLoaded', function() {
  applyThemeToPreview();
});
</script>
```

### Крок 1E — синхронізація з `pv_theme` (глобальна тема)

Якщо `pv_preview_theme == 'auto'`, фрейм слухає ті самі події зміни теми, що й головна сторінка. Якщо `'light'` або `'dark'` — ігнорує глобальну тему. Це реалізовано в функції `applyThemeToPreview()`.

---

## Підсумок виконання:

| Крок | Дія | Статус |
|------|-----|--------|
| 1A | Зчитати `viewer_help.md` і перетворити на HTML строку | ✅ |
| 1B | Додати кнопки «ℹ️ Опис» і «🎨 Тема в прев'ю» у `<header>` | ✅ |
| 1C | Додати прихований `<div id="helpFrame">` з HELP_HTML | ✅ |
| 1D | Додати JS-обробники кліків + `localStorage('pv_preview_theme')` | ✅ |
| 1E | Синхронізація: auto → слідкує за pv_theme; light/dark → фіксовано | ✅ |
| 2A | Створити `installer/viewer_setup.iss` з логікою перевірки/встановлення | ✅ |
| 2B | Додати `installer/__init__.py`, `LICENSE.txt`, `README.md` | ✅ |
| 3 | Перевірити `render_xlsx()` — немає темної теми для таблиці ✅ | ✅ (додано background:#fff) |
| 4 | Запустити `python generate_viewer.py`, перевірити наявність UI-елементів | ✅ |
| 5 | Видалити `_tx_*`, `_sv_*` артефакти, залишити службові | ✅ (порожньо) |

---
