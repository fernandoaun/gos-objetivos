@echo off
REM Baja el estado actual de Render a instance\prueba (solo local).
REM NO modifica Render.
cd /d "%~dp0"
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo   GOS — Bajar Render a base de PRUEBA local
echo   Destino: instance\prueba\gos.db
echo   Remoto: solo LECTURA
echo.

set "GOS_DATABASE_PATH=%CD%\instance\prueba\gos.db"
set "DATABASE_URL="
set "FLASK_ENV=development"

"%PY%" scripts\bajar_render_a_prueba.py
echo.
pause
