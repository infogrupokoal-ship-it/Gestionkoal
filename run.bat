@echo off
cd /d %~dp0
set FLASK_APP=backend:create_app
set FLASK_DEBUG=1
venv\Scripts\python.exe -m flask run