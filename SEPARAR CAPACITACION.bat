@echo off
REM Separa Cap y Objetivos en dos bases (conserva origen + backup).
cd /d "%~dp0"
echo.
echo === Separar Capacitación / Objetivos (Option B) ===
echo.
python scripts\separar_bases_capacitacion.py %*
if errorlevel 1 (
  echo.
  echo Fallo la separacion. Revisá el mensaje arriba.
  pause
  exit /b 1
)
echo.
pause
