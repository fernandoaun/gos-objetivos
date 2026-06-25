@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

echo ====================================================
echo   GOS — Verificar variables de entorno
echo ====================================================
echo.
"%PY%" scripts\check_env.py
if errorlevel 1 pause
exit /b %ERRORLEVEL%
