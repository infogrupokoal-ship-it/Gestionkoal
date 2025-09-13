@echo off
cd /d %~dp0
start "Flask Server" cmd /k "set FLASK_APP=backend:create_app && set FLASK_DEBUG=1 && venv\Scripts\python.exe -m flask run"