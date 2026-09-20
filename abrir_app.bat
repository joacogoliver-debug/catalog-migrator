@echo off
REM Abre el Migrador de Catalogos desde el codigo fuente (Windows).
REM Para el ejecutable ya compilado no hace falta esto: es doble clic.
REM
REM Los mensajes van en los dos idiomas. Este script corre ANTES que la app, y
REM por lo tanto antes de que exista i18n: no hay de donde sacar el idioma
REM elegido, asi que se dicen las dos cosas en vez de suponer una.

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo No encontre Python. Instalalo desde https://www.python.org/downloads/
  echo Acordate de tildar "Add Python to PATH" durante la instalacion.
  echo.
  echo Python not found. Install it from https://www.python.org/downloads/
  echo Remember to tick "Add Python to PATH" during the install.
  pause
  exit /b 1
)

python -c "import openpyxl" >nul 2>nul
if errorlevel 1 (
  echo Instalando dependencias por primera vez... / Installing dependencies for the first time...
  python -m pip install -r requirements-app.txt
)

echo Abriendo el Migrador de Catalogos... / Opening Catalog Migrator...
python app\launcher.py
if errorlevel 1 pause
