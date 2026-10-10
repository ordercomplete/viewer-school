@echo off
rem Viewer-for-School - generate viewer.html for a chosen materials folder
rem NOTE: keep this file ASCII-only (cmd parser); the picker gets Ukrainian text
rem via -EncodedCommand (UTF-16LE base64), Python prints its own Ukrainian output.
chcp 65001 >nul
setlocal

rem Search base: current working directory (no hardcoding of the script folder).
set "SEARCH_DIR=."

rem Materials folder: first argument (drop a folder onto the shortcut), otherwise
rem the default 'I semestr' folder next to this script; if not found, try 'II semestr'.
set "ROOT=%~1"
if not "%ROOT%"=="" goto validate_root

set "ROOT=%SEARCH_DIR%\I semestr"
if exist "%ROOT%\" (
    goto validate_root
)

set "ROOT=%SEARCH_DIR%\II semestr"
if exist "%ROOT%\" (
    goto validate_root
)

rem Neither semester folder found - show clear error with what was searched
rem (so the user sees exactly which path was tried).
echo.
echo ERROR: materials folder not found.
echo   Searched base: "%SEARCH_DIR%"
echo   Folders checked:
echo     "I semestr" = not found
echo     "II semestr" = not found
echo   You can:
echo     - place the folder in the current directory and name it 'I semestr' or 'II semestr'
echo     - or pass the full path as an argument: generate_for.bat "D:\path\to\your\folder"
echo.
pause
exit /b 1

:validate_root
rem Strip a trailing backslash (see start_viewer.bat for the reason)
if "%ROOT:~-1%"=="\\" if not "%ROOT:~1,1%"==":" set "ROOT=%ROOT:~0,-1%"
if not exist "%ROOT%\\" (
    echo.
    echo ERROR: materials folder not found.
    echo   Searched: "%ROOT%"
    echo   Expected: a folder named "I semestr" or "II semestr" next to generate_for.bat
    echo   (the one you moved the main content into).
    echo   Check the folder name - it must be exactly 'I semestr' or 'II semestr'.
    echo.
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

echo Done: "%ROOT%\\viewer.html"
pause