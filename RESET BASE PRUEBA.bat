@echo off
REM Restaura la base de prueba desde el ultimo snapshot (pisa cambios de prueba).
cd /d "%~dp0"
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
echo.
echo   GOS — Reset base de PRUEBA desde snapshot
echo.
"%PY%" scripts\preparar_local_prueba.py --desde-snapshot --reset
echo.
pause
