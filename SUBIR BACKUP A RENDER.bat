@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

echo ====================================================
echo   GOS — Subir backup a Render
echo ====================================================
echo.
echo Este metodo sube tu base local a la MISMA base
echo que usa el servicio en Render.
echo.
echo 1. En Render: servicio "gos-objetivos" ^> Environment
echo 2. Copia el valor de GOS_IMPORT_SECRET a tu .env local
echo    o pegalo cuando te lo pida el script.
echo 3. Guarda y espera que redeploye (Live)
echo.
if not defined GOS_IMPORT_SECRET (
    set /p GOS_IMPORT_SECRET="GOS_IMPORT_SECRET: "
)
if "%GOS_IMPORT_SECRET%"=="" (
    echo ERROR: falta GOS_IMPORT_SECRET.
    pause
    exit /b 1
)
echo.
"%PY%" scripts\subir_backup_a_render.py
if errorlevel 1 (
    echo.
    echo ERROR. Si dice 403: revisa que GOS_IMPORT_SECRET coincida en Render y local.
    pause
    exit /b 1
)
echo.
echo Verifica en el navegador:
echo https://gos-objetivos.onrender.com/gos/objetivos/api/v1/health?db=1
echo.
pause
