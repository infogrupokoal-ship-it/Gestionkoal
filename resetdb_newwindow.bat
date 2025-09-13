@echo off
cd /d %~dp0
start "Flask ResetDB" cmd /k "set FLASK_APP=backend:create_app && venv\Scripts\python.exe -m flask init-db && echo. && echo [OK] Base de datos reinicializada. && pause"