@echo off
rem Runs Murmur with a console window so you can see logs live.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m murmur
pause
