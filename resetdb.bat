@echo off
cd /d %~dp0
set FLASK_APP=backend:create_app
echo Cerrando locks SQLite...
del /q instance\*.sqlite-wal 2>nul
del /q instance\*.sqlite-shm 2>nul
del /q instance\*.sqlite-journal 2>nul
echo Borrando BD...
del /q instance\backend.sqlite 2>nul
echo Inicializando BD...
venv\Scripts\python.exe -m flask init-db
echo [OK] BD reinicializada.
pause