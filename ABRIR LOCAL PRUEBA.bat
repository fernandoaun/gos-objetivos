@echo off
REM Abre GOS en local con una copia de la base (instance\prueba).
REM NO usa la base de Render. Los cambios quedan solo en esta PC.
REM Puerto 5001 para no chocar con otros programas en :5000
cd /d "%~dp0"

set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo   GOS — Local de PRUEBA (aislado de Render)
echo.

if not exist "%CD%\instance\prueba\gos.db" (
  echo   Primera vez: copiando base de hoy a instance\prueba ...
  "%PY%" scripts\preparar_local_prueba.py --reset
) else (
  "%PY%" scripts\preparar_local_prueba.py
)
if errorlevel 1 (
  echo ERROR al preparar la base de prueba.
  pause
  exit /b 1
)

REM Forzar SQLite local de prueba — nunca Postgres/Render
set "GOS_DATABASE_PATH=%CD%\instance\prueba\gos.db"
set "GOS_VACACIONES_DB_PATH=%CD%\instance\prueba\vacaciones\indicadores.db"
set "GOS_HWO_DATA_DIR=%CD%\instance\prueba\hwo"
set "GOS_LOCAL_DB_PATH=%CD%\instance\prueba\gos.db"
set "DATABASE_URL="
set "RENDER_DATABASE_URL="
set "FLASK_ENV=development"
set "GOS_AUTO_LOGIN=true"
set "GOS_PORT=5001"

REM Liberar solo el puerto de PRUEBA (5001), no el 5000 de otros programas
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5001" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)

echo.
echo   Base:  instance\prueba\gos.db
echo   URL:   http://127.0.0.1:5001/
echo   Remoto: NO se toca (no subas backup mientras pruebes)
echo.
echo   Entra sin login (auto-login).
echo   NO CIERRES esta ventana mientras uses el sistema.
echo.

"%PY%" run.py
pause
