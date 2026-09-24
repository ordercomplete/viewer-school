@echo off
rem Viewer-for-School - generate viewer.html for a chosen materials folder
rem NOTE: keep this file ASCII-only (cmd parser); the picker gets Ukrainian text
rem via -EncodedCommand (UTF-16LE base64), Python prints its own Ukrainian output.
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem Folder may come as the first argument (drop a folder onto the shortcut)...
set "ROOT=%~1"
if not "%ROOT%"=="" goto have_root

rem ...otherwise ask the user with a folder picker dialog
for /f "usebackq delims=" %%i in (`powershell -NoProfile -NonInteractive -EncodedCommand QQBkAGQALQBUAHkAcABlACAALQBBAHMAcwBlAG0AYgBsAHkATgBhAG0AZQAgAFMAeQBzAHQAZQBtAC4AVwBpAG4AZABvAHcAcwAuAEYAbwByAG0AcwAKACQAZAAgAD0AIABOAGUAdwAtAE8AYgBqAGUAYwB0ACAAUwB5AHMAdABlAG0ALgBXAGkAbgBkAG8AdwBzAC4ARgBvAHIAbQBzAC4ARgBvAGwAZABlAHIAQgByAG8AdwBzAGUAcgBEAGkAYQBsAG8AZwAKACQAZAAuAEQAZQBzAGMAcgBpAHAAdABpAG8AbgAgAD0AIAAnAB4EMQQ1BEAEVgRCBEwEIABCBDUEOgRDBCAANwQgAD0EMAQyBEcEMAQ7BEwEPQQ4BDwEOAQgADwEMARCBDUEQARWBDAEOwQwBDwEOAQgACgAOgQ+BEAEVgQ9BEwEIABCBDUEOgQ4BCAANwQgAD8EQAQ1BDQEPAQ1BEIEMAQ8BDgEKQAnAAoAJABkAC4AUwBoAG8AdwBOAGUAdwBGAG8AbABkAGUAcgBCAHUAdAB0AG8AbgAgAD0AIAAkAGYAYQBsAHMAZQAKAGkAZgAgACgAJABkAC4AUwBoAG8AdwBEAGkAYQBsAG8AZwAoACkAIAAtAGUAcQAgAFsAUwB5AHMAdABlAG0ALgBXAGkAbgBkAG8AdwBzAC4ARgBvAHIAbQBzAC4ARABpAGEAbABvAGcAUgBlAHMAdQBsAHQAXQA6ADoATwBLACkAIAB7ACAAJABkAC4AUwBlAGwAZQBjAHQAZQBkAFAAYQB0AGgAIAB9AA==`) do set "ROOT=%%i"

:have_root
if "%ROOT%"=="" (
    echo Cancelled: no folder selected.
    pause
    exit /b 1
)
rem Strip a trailing backslash (see start_viewer.bat for the reason)
if "%ROOT:~-1%"=="\" if not "%ROOT:~1,1%"==":" set "ROOT=%ROOT:~0,-1%"
if not exist "%ROOT%\" (
    echo ERROR: folder not found: "%ROOT%"
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

echo Materials folder: "%ROOT%"
python "%~dp0install_deps.py" || (
    echo ERROR: could not prepare Python dependencies.
    pause
    exit /b 1
)

python "%~dp0generate_viewer.py" "%ROOT%" || (
    echo ERROR: page generation failed.
    pause
    exit /b 1
)

echo Done: "%ROOT%\viewer.html"
pause
