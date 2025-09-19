@echo off
REM Initialize or migrate DB using Flask CLI 'init-db' command implemented in your app.
setlocal
call 00_setup_venv.bat >nul
call 01_detect_flask_app.bat
if errorlevel 1 (
  echo [!] Please set FLASK_APP manually inside this file.
  pause
  exit /b 1
)
echo [i] Activating venv...
call venv\Scripts\activate
echo [i] Running: flask --app %FLASK_APP% init-db
flask --app %FLASK_APP% init-db
endlocal
pause
