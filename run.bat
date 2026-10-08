@echo off
rem Starts Murmur. If it's already running, this just brings its window forward.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m murmur
