@echo off
cd /d C:\proyecto\gestion_avisos
set FLASK_APP=backend
set FLASK_ENV=production
set PYTHONUTF8=1
echo [%date% %time%] Starting Flask --no-reload > logs\server_output_10.log
.venv\Scripts\flask.exe run --host=127.0.0.1 --port=5000 --no-reload >> logs\server_output_10.log 2>&1