@echo off
REM Lanzador silencioso para la tarea programada "GOS-Backup-Diario"
cd /d "%~dp0.."
set "LOG=%CD%\instance\backups\backup-diario.log"
set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
if not exist "%CD%\instance\backups" mkdir "%CD%\instance\backups"
echo.>> "%LOG%"
echo ===== %DATE% %TIME% =====>> "%LOG%"
"%PY%" "%CD%\scripts\backup_local.py" >> "%LOG%" 2>&1
exit /b %ERRORLEVEL%
