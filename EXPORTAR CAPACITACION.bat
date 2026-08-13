@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === Exportar paquete Capacitación (copia segura) ===
echo No modifica instance\gos.db ni Render.
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" scripts\exportar_capacitacion_paquete.py %*
if errorlevel 1 (
    echo.
    echo ERROR al exportar.
    pause
    exit /b 1
)

echo.
echo Abrí la carpeta exports\
explorer "exports"
pause
