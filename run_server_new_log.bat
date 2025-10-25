@echo off
set FLASK_APP=backend
set FLASK_DEBUG=1
echo Starting server... > C:\proyecto\gestion_avisos\logs\server_output_2.log
C:\proyecto\gestion_avisos\.venv\Scripts\flask.exe run --host=0.0.0.0 --no-reload >> C:\proyecto\gestion_avisos\logs\server_output_2.log 2>&1
