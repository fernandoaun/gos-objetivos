@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

echo ====================================================
echo   GOS Objetivos — Importar datos locales a Render
echo ====================================================
echo.
echo 1. Entra a https://dashboard.render.com
echo 2. Abre la base "gos-objetivos-db"
echo 3. Pestaña Connections ^> External Database URL
echo 4. Copia la URL completa (postgresql://...)
echo.
echo IMPORTANTE: debe ser la base "gos-objetivos-db", NO otra URL.
echo.
set /p RENDER_DATABASE_URL="Pega aqui la External Database URL: "
if "%RENDER_DATABASE_URL%"=="" (
    echo ERROR: no pegaste ninguna URL.
    pause
    exit /b 1
)
echo.
echo Preparando dependencias...
"%PY%" -m pip install psycopg2-binary -q
if errorlevel 1 (
    echo ERROR: no se pudo instalar psycopg2-binary.
    pause
    exit /b 1
)
echo Importando base local ...
set RENDER_DATABASE_URL=%RENDER_DATABASE_URL%
"%PY%" scripts\importar_local_a_render.py
if errorlevel 1 (
    echo.
    echo ERROR en la importacion. Revisa la URL y tu conexion a internet.
    pause
    exit /b 1
)
echo.
echo ====================================================
echo   Listo. Entra a:
echo   https://gos-objetivos.onrender.com
echo   Usuario y clave: ver GOS_ADMIN_* en Render Environment
echo ====================================================
pause

