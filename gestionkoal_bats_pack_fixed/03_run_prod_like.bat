@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 03_run_prod_like (Waitress) - Gestionkoal
if exist "env.local.bat" call "env.local.bat"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

set "APP_HOST=0.0.0.0"
set "APP_PORT=5000"
set "APP_THREADS=4"

echo [*] Waitress (local) http://127.0.0.1:%APP_PORT%/
waitress-serve --host=%APP_HOST% --port=%APP_PORT% --call backend:create_app --threads=%APP_THREADS%
