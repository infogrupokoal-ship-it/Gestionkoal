@echo off
REM Start Flask development server with auto-reload
setlocal
call 00_setup_venv.bat >nul

call 01_detect_flask_app.bat
if errorlevel 1 (
  echo.
  echo [!] Edit 02_run_dev.bat and hardcode FLASK_APP if detection fails.
  echo     Example: set FLASK_APP=backend:create_app
  pause
  exit /b 1
)

set FLASK_ENV=development
set FLASK_DEBUG=1
set FLASK_RUN_PORT=5000
set FLASK_RUN_HOST=127.0.0.1

echo [i] Activating venv...
call venv\Scripts\activate

echo [i] Running: flask --app %FLASK_APP% run --host=%FLASK_RUN_HOST% --port=%FLASK_RUN_PORT%
start "" "http://%FLASK_RUN_HOST%:%FLASK_RUN_PORT%/"
flask --app %FLASK_APP% run --host=%FLASK_RUN_HOST% --port=%FLASK_RUN_PORT%
endlocal
