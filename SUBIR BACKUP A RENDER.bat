@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

echo ====================================================
echo   GOS Objetivos — Subir backup a Render
echo ====================================================
echo.
echo Este metodo sube tu base local a la MISMA base
echo que usa https://gos-objetivos.onrender.com
echo.
echo 1. En Render abri el servicio "gos-objetivos"
echo 2. Environment ^> agrega o revisa:
echo      GOS_IMPORT_SECRET = gos-restaurar-datos
echo 3. Guarda y espera que redeploye (Live)
echo.
set /p GOS_IMPORT_SECRET="Pega el valor de GOS_IMPORT_SECRET: "
if "%GOS_IMPORT_SECRET%"=="" (
    echo ERROR: falta la clave.
    pause
    exit /b 1
)
echo.
"%PY%" scripts\subir_backup_a_render.py
if errorlevel 1 (
    echo.
    echo ERROR. Si dice 403: revisa GOS_IMPORT_SECRET en Render.
    echo Si dice 404: espera a que termine el deploy del ultimo push.
    pause
    exit /b 1
)
echo.
echo Verifica en el navegador:
echo https://gos-objetivos.onrender.com/api/v1/health?db=1
echo Debe mostrar foda_items: 86
echo.
pause
