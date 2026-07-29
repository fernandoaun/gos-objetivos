@echo off
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo   GOS — Backup local ahora
echo.
"%PY%" scripts\backup_local.py --snapshot manual
echo.
pause
