@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 10_db_upgrade (Alembic/Flask) - Gestionkoal
if exist "env.local.bat" call "env.local.bat"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set "FLASK_APP=backend:create_app"
echo [*] flask db upgrade ...
python -m flask db upgrade
if errorlevel 1 (
  echo [!] Error en migraciones. Revisa el mensaje anterior.
  exit /b 1
)
echo [+] Migraciones aplicadas.
