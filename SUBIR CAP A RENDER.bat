@echo off
REM Sube instance\capacitacion\gos_cap.db al Postgres de Cap en Render.
cd /d "%~dp0"
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo === Subir Capacitación a Render (DB Cap) ===
echo.
echo 1. Render → gos-capacitacion-db → Connect → External Database URL
echo 2. Pegala abajo (o tenela en .env como RENDER_CAP_DATABASE_URL)
echo.

if not defined RENDER_CAP_DATABASE_URL (
  set /p RENDER_CAP_DATABASE_URL="RENDER_CAP_DATABASE_URL: "
)
if "%RENDER_CAP_DATABASE_URL%"=="" (
  echo ERROR: falta RENDER_CAP_DATABASE_URL.
  pause
  exit /b 1
)

"%PY%" scripts\subir_cap_a_render.py
if errorlevel 1 (
  echo ERROR al subir Cap.
  pause
  exit /b 1
)
echo.
pause
