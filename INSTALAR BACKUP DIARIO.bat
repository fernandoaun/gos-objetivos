@echo off
REM Instala / actualiza la tarea programada GOS-Backup-Diario (Windows).
REM Copia diariamente instance/gos.db y datos relacionados a instance/backups/
REM Retención: 14 días (ver scripts/backup_local.py --keep).

cd /d "%~dp0"
set "TASK=GOS-Backup-Diario"
set "BAT=%~dp0scripts\run_backup_diario.bat"
set "HORA=19:00"

if not exist "%BAT%" (
  echo ERROR: no existe %BAT%
  pause
  exit /b 1
)

echo.
echo   GOS — Instalar backup diario automatico
echo   Tarea: %TASK%
echo   Hora:  %HORA% todos los dias
echo   Script: %BAT%
echo.

schtasks /Create /TN "%TASK%" /TR "\"%BAT%\"" /SC DAILY /ST %HORA% /F /RL LIMITED >nul
if errorlevel 1 (
  echo ERROR al crear la tarea. Proba ejecutar este .bat como Administrador.
  pause
  exit /b 1
)

echo Tarea creada/actualizada.
echo.
echo Probando backup ahora...
call "%BAT%"
echo.
echo Proxima ejecucion programada:
schtasks /Query /TN "%TASK%" /FO LIST | findstr /I "proxima Nombre Estado"
echo.
echo Backups en: %~dp0instance\backups\
echo Log:        %~dp0instance\backups\backup-diario.log
echo.
pause
