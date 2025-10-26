 @echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  py -3 -m venv .venv || (echo [!] No se pudo crear el venv & exit /b 1)
)
call .venv\Scripts\activate.bat

pip install --upgrade pip >nul
pip install -r requirements.txt || (echo [!] pip install fallo & exit /b 1)

set FLASK_APP=backend:create_app
set FLASK_ENV=production
if not defined SECRET_KEY set SECRET_KEY=local-dev-secret
if not defined PORT set PORT=5000

if not exist "instance" mkdir instance >nul 2>&1

echo [*] Iniciando Waitress en http://127.0.0.1:%PORT% ...
python -m waitress --listen=127.0.0.1:%PORT% --threads=4 --call backend:create_app
