@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 02_run_dev (Flask dev) - Gestionkoal
if exist "env.local.bat" call "env.local.bat"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set "FLASK_APP=backend:create_app"
set "FLASK_RUN_HOST=127.0.0.1"
set "FLASK_RUN_PORT=5000"

echo [*] Flask dev en http://%FLASK_RUN_HOST%:%FLASK_RUN_PORT%/
python -m flask run --host=%FLASK_RUN_HOST% --port=%FLASK_RUN_PORT%
