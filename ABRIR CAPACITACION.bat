@echo off
cd /d "%~dp0"
wscript.exe //B "%~dp0ABRIR CAPACITACION.vbs"
exit /b %ERRORLEVEL%
