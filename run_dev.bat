@echo off
setlocal ENABLEEXTENSIONS

REM ===== Arranque de desarrollo (Windows) =====
REM Usa la variable (o argumento) para indicar la factoría de app FLASK.
REM Ej.: run_dev.bat app:create_app

set APP_MODULE=backend:create_app
if not "%~1"=="" set APP_MODULE=%~1

if not exist "venv" (
  echo [!] No existe venv. Ejecuta primero start_local.bat
  exit /b 1
)

call "venv\Scripts\activate"
set FLASK_APP=%APP_MODULE%
set FLASK_ENV=development

echo [+] Ejecutando servidor: flask --app %FLASK_APP% run --port 5000
flask --app %FLASK_APP% run --port 5000
