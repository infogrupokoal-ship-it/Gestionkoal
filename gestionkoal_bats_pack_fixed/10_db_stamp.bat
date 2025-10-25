@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 10_db_stamp (Alembic/Flask) - Gestionkoal
if exist "env.local.bat" call "env.local.bat"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set "FLASK_APP=backend:create_app"
if "%~1"=="" (
  echo Uso: 10_db_stamp.bat <revision>
  echo Ej:   10_db_stamp.bat head
  exit /b 1
)
python -m flask db stamp %1
