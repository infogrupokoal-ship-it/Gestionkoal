@echo off
echo [TEST_SCRIPT] Changing to project directory...
cd C:\proyecto\gestion_avisos

echo [TEST_SCRIPT] Activating virtual environment...
call .\.venv\Scripts\activate

echo [TEST_SCRIPT] Cleaning up previous log file...
if exist "C:\proyecto\gestion_avisos\1_gemini\logs\server_run.log" del "C:\proyecto\gestion_avisos\1_gemini\logs\server_run.log"

echo [TEST_SCRIPT] Starting server in background...
start /B waitress-serve --host=127.0.0.1 --port=5000 backend:create_app > C:\proyecto\gestion_avisos\1_gemini\logs\server_run.log 2>&1

echo [TEST_SCRIPT] Server process started. Output is being redirected to server_run.log.
timeout /t 5 > nul
echo [TEST_SCRIPT] Done.
