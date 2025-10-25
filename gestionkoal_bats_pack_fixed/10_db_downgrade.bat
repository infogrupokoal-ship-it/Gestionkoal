@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 10_db_downgrade (Alembic/Flask) - Gestionkoal
if exist "env.local.bat" call "env.local.bat"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set "FLASK_APP=backend:create_app"
if "%~1"=="" (
  echo Uso: 10_db_downgrade.bat <revision>
  echo Ej:   10_db_downgrade.bat -1
  exit /b 1
)
python -m flask db downgrade %1
