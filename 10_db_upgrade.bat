@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
set "ROOT=%~dp0.."
echo [START] 10_db_upgrade (ROOT=%ROOT%)
if exist "%ROOT%\.venv\Scripts\activate.bat" call "%ROOT%\.venv\Scripts\activate.bat"
set "FLASK_APP=backend:create_app"
pushd "%ROOT%"
python -m flask db upgrade
set "ERR=%ERRORLEVEL%" 
popd
if not "%ERR%"=="0" echo [!] Error en migraciones: %ERR%
if not defined NO_PAUSE pause
