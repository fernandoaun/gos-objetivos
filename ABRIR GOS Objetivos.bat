@echo off
REM Sin ventanas negras: delega en el lanzador silencioso (.vbs)
cd /d "%~dp0"
wscript.exe //B "%~dp0ABRIR GOS Objetivos.vbs"
exit /b %ERRORLEVEL%
