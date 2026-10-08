@echo off
setlocal
rem Removes Murmur's shortcuts and private Python environment, and optionally your history and settings.
cd /d "%~dp0"
title Uninstall Murmur
echo.
echo   Uninstall Murmur
echo   ----------------
echo   First quit Murmur: right-click its icon in the taskbar tray and choose "Quit Murmur".
echo.
pause

echo Removing shortcuts...
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do del /q "%%D\Murmur.lnk" 2>nul
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Murmur.lnk" 2>nul
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Murmur.lnk" 2>nul

echo Removing Murmur's Python environment (this frees about 3 GB)...
if exist .venv rmdir /s /q .venv

echo.
choice /c YN /m "Also delete your dictation history and settings"
if errorlevel 2 goto :models
rmdir /s /q "%APPDATA%\Murmur" 2>nul
echo History and settings deleted.

:models
echo.
choice /c YN /m "Also delete the downloaded speech models (0.5 to 3 GB)"
if errorlevel 2 goto :done
for /d %%M in ("%USERPROFILE%\.cache\huggingface\hub\models--*whisper*") do rmdir /s /q "%%M"
echo Speech models deleted.

:done
echo.
echo Murmur is uninstalled. You can now delete this folder:
echo   %~dp0
pause
