@echo off
setlocal ENABLEEXTENSIONS

REM ===== Inicializar DB (Windows) =====
REM Usa la variable (o argumento) para indicar la factoría de app FLASK.
REM Ej.: init_db.bat app:create_app

set APP_MODULE=backend:create_app
if not "%~1"=="" set APP_MODULE=%~1

if not exist "venv" (
  echo [!] No existe venv. Ejecuta primero start_local.bat
  exit /b 1
)

call "venv\Scripts\activate"
set FLASK_APP=%APP_MODULE%

echo [+] Ejecutando: flask --app %FLASK_APP% init-db
flask --app %FLASK_APP% init-db
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% NEQ 0 (
  echo [X] Error al inicializar la base de datos. Codigo %EXITCODE%.
  exit /b %EXITCODE%
)

echo [OK] Base de datos inicializada.
exit /b 0
