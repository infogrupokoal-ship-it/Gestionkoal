@echo off
REM Initialize or migrate DB using Flask CLI 'init-db' command implemented in your app.
setlocal
call 00_setup_venv.bat >nul
set FLASK_APP=backend:create_app
echo [i] Activating venv...
call venv\Scripts\activate
echo [i] Running: flask --app %FLASK_APP% init-db
flask --app %FLASK_APP% init-db
endlocal
pause
