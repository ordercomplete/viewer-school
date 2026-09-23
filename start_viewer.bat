@echo off
chcp 65001 >nul
cd /d "%~dp0"
for %%f in (generate_viewer.py viewer_server.py viewer_probe.py) do (
    if not exist "%%f" echo Missing %%f & exit /b 1
)
python generate_viewer.py
python viewer_server.py --open
pause
