# Інсталятор viewer

Використайте Inno Setup Compiler (`iscc`) для створення `.exe`:

```powershell
iscc.exe viewer_setup.iss
```

## Скрипт `viewer_setup.iss` робить наступне:

1. **Перевіряє наявність Python 3.8+** — якщо відсутній, попереджає і пропонує встановити.

2. **Сторінка з умовами використання:**
   ```
   Ця програма призначена для дистанційного заочного навчання старших класів середньої школи.
   Використовується безкоштовно як є, без претензій.
   ```

3. **Сторінка попередження про необхідне ПЗ:**
   ```
   - Python 3.8+
   - openpyxl
   - python-pptx
   - Pillow (PIL)
   
   Якщо компоненти відсутні, інсталятор спробує їх встановити через pip.
   ```

4. **Після згоди:**
   - Спочатку виконує `pip install openpyxl python-pptx Pillow --quiet`.
   - Потім копіює файли програми до обраної папки.

5. **Файли, що копіюються:**
   - `generate_viewer.py`
   - `viewer_server.py`
   - `viewer_probe.py`
   - `start_viewer.bat`
   - `viewer.html` (шаблон)
   - `viewer_help.md`
   - `installer/__init__.py`
   - папка `viewer_assets/` (якщо існує)

6. **Ярлики:**
   - «📚 Перегляд матеріалів» → `start_viewer.bat`
   - «Згенерувати для теки…» → `cmd /k generate_driver.py "%~dp0"` (або через python.exe)

7. **Деінсталятор** видаляє ярлики, файли залишаються на диску (користувач може інсталювати в `Las Папку навчання`).

---

## Як зібрати:

```powershell
# Встановіть Inno Setup Compiler (https://jrsoftware.org/isdl.php)
iscc.exe "J:\328_11-D\I semestr\installer\viewer_setup.iss"
```

Після компіляції у папці `Output` з'явиться файл `ViewerSchoolSetup.exe`.
