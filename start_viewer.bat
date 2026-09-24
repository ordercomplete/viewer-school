@echo off
rem Viewer-for-School - quick start: prepare deps -> generate page -> run local server
rem NOTE: keep this file ASCII-only. Ukrainian messages come from the Python scripts.
chcp 65001 >nul
setlocal
cd /d "%~dp0"

for %%f in (generate_viewer.py viewer_server.py viewer_probe.py install_deps.py) do if not exist "%%f" (
    echo ERROR: missing file %%f
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    echo Install Python 3.8+ from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup.
    pause
    exit /b 1
)

rem Materials folder: first argument, otherwise the folder of this script
set "PV_ROOT=%~1"
if "%PV_ROOT%"=="" set "PV_ROOT=%~dp0"
rem Strip a trailing backslash: in "...\" cmd+MSVCRT would turn the closing
rem quote into a literal one and Python would see a path ending with '"'
if "%PV_ROOT:~-1%"=="\" if not "%PV_ROOT:~1,1%"==":" set "PV_ROOT=%PV_ROOT:~0,-1%"

python "%~dp0install_deps.py" || (
    echo ERROR: could not prepare Python dependencies.
    pause
    exit /b 1
)

python "%~dp0generate_viewer.py" "%PV_ROOT%" || (
    echo ERROR: page generation failed.
    pause
    exit /b 1
)

python "%~dp0viewer_server.py" --open --root "%PV_ROOT%"
pause
