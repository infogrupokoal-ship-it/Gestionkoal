@echo off
REM =====================================================
REM  KOAL - Start Local (Waitress / "production-like")
REM =====================================================
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo [1/7] Buscando Python...
where py >NUL 2>&1 || where python >NUL 2>&1 || (
  echo [ERROR] Python no encontrado. Instala Python desde https://www.python.org/ y marca "Add to PATH".
  pause
  exit /b 1
)

echo [2/7] Creando entorno .venv (si no existe)...
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv 2>NUL || python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual .venv
    pause
    exit /b 1
  )
)

echo [3/7] Activando .venv...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] No se pudo activar el entorno .venv
  pause
  exit /b 1
)

echo [4/7] Instalando dependencias...
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Fallo instalando dependencias. Si el error es por "psycopg2":
  echo         - En local usa SQLite (no hace falta psycopg2).
  echo         - Edita requirements.txt y elimina la linea de psycopg2/psycopg2-binary.
  pause
  exit /b 1
)

echo [5/7] Variables del entorno...
if "%DB_PATH%"=="" set "DB_PATH=database.db"
if "%UPLOAD_FOLDER%"=="" set "UPLOAD_FOLDER=uploads"
set "FLASK_APP=app.py"
echo        DB_PATH=%DB_PATH%
echo        UPLOAD_FOLDER=%UPLOAD_FOLDER%

echo [6/7] Asegurando carpetas/DB...
if not exist "%UPLOAD_FOLDER%" mkdir "%UPLOAD_FOLDER%"
if not exist "%DB_PATH%" (
  echo      Inicializando base de datos...
  py -m flask init-db || python -m flask init-db
  if errorlevel 1 (
    echo [ERROR] No se pudo inicializar la base de datos (flask init-db).
    pause
    exit /b 1
  )
)

echo [7/7] Iniciando servidor con waitress (http://127.0.0.1:5000)...
py run_waitress.py || python run_waitress.py
if errorlevel 1 (
  echo [ERROR] El servidor se cerro con error.
  pause
  exit /b 1
)

endlocal
