@echo off
REM ===============================
REM  Grupo Koal - Start Local App
REM  Project path: C:\proyecto\gestion_avisos
REM ===============================

cd /d "%~dp0"

echo === 1) Creating virtual environment (if missing) ===
if not exist ".venv" (
  python -m venv .venv
)

echo === 2) Activating virtual environment ===
call .venv\Scripts\activate.bat

echo === 3) Installing dependencies ===
pip install --upgrade pip
pip install -r requirements.txt

echo === 4) Environment variables ===
set FLASK_APP=app.py
if "%DB_PATH%"=="" set DB_PATH=database.db
if "%UPLOAD_FOLDER%"=="" set UPLOAD_FOLDER=uploads

echo Using DB_PATH=%DB_PATH%
echo Using UPLOAD_FOLDER=%UPLOAD_FOLDER%

echo === 5) Initialize database (if missing) ===
if not exist "%DB_PATH%" (
  echo database not found at "%DB_PATH%". Running "flask init-db"...
  flask init-db
) else (
  echo database already exists at "%DB_PATH%". Skipping init.
)

echo === 6) Starting server with waitress ===
python run_waitress.py

pause
