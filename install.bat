@echo off
setlocal
rem One-time setup: finds (or installs) Python, creates a private environment, installs
rem the libraries, downloads the speech model and adds Murmur to the desktop and Start Menu.
cd /d "%~dp0"
title Murmur setup
echo.
echo   Murmur setup
echo   ------------
echo   This takes 5 to 15 minutes the first time, depending on your internet.
echo   You can leave this window open and do something else.
echo.

rem ---- 1. Find Python 3.11, 3.12 or 3.13 ----
set "PY="
if exist .venv\Scripts\python.exe goto :have_venv
for %%V in (3.13 3.12 3.11) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if (3, 11) <= sys.version_info < (3, 14) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY goto :install_python

echo [1/4] Creating Murmur's private Python environment...
%PY% -m venv .venv || goto :error

:have_venv
set "VPY=.venv\Scripts\python.exe"

rem ---- 2. Libraries (plus the NVIDIA libraries only if this PC has an NVIDIA GPU) ----
set "MODE=cpu"
where nvidia-smi >nul 2>&1 && set "MODE=gpu"
echo.
if "%MODE%"=="gpu" (
  echo [2/4] NVIDIA graphics card found. Murmur will use it for fast, accurate dictation.
) else (
  echo [2/4] No NVIDIA graphics card found. Murmur will run on your processor with a
  echo       smaller model. It still works well, just a little slower.
)
echo       Installing libraries...
"%VPY%" -m pip install --upgrade pip --quiet || goto :error
"%VPY%" -m pip install -r requirements.txt || goto :error
if "%MODE%"=="gpu" (
  "%VPY%" -m pip install -r requirements-gpu.txt || goto :error
)

rem ---- 3. Speech model ----
echo.
echo [3/4] Getting the speech model...
"%VPY%" tools\install_helper.py %MODE% || goto :error

rem ---- 4. Shortcuts ----
echo.
echo [4/4] Adding Murmur to your desktop and Start Menu...
"%VPY%" -c "from murmur.winintegration import create_desktop_and_start_menu as c; c()" || goto :error

echo.
echo   All done!
echo   Murmur is starting now. Click into any text box, hold Ctrl + Alt, speak, and let go.
echo   Next time, open it from the Murmur icon on your desktop.
echo.
start "" ".venv\Scripts\pythonw.exe" -m murmur
pause
exit /b 0

:install_python
echo Murmur needs Python 3.11, 3.12 or 3.13, and none was found on this PC.
echo Trying to install Python 3.12 for you with winget...
echo.
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :python_manual
echo.
echo Python is installed. Please close this window and double-click install.bat again.
pause
exit /b 0

:python_manual
echo.
echo Automatic install did not work. Please install Python yourself:
echo   1. Open https://www.python.org/downloads/windows/
echo   2. Download a Python 3.12 "Windows installer (64-bit)" and run it.
echo   3. IMPORTANT: tick "Add python.exe to PATH" on the first screen.
echo   4. Then double-click install.bat again.
start "" "https://www.python.org/downloads/windows/"
pause
exit /b 1

:error
echo.
echo Setup stopped because of an error (see the messages above).
echo Common fixes: check your internet connection, make sure you have about 4 GB free,
echo then run install.bat again. It picks up where it left off.
echo Still stuck? Open an issue: https://github.com/Abhijay-Nagal/murmur/issues
pause
exit /b 1
