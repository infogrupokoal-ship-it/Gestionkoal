@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
set "ROOT=%~dp0.."
echo [START] 02_run_dev (ROOT=%ROOT%)
if exist "%ROOT%\.venv\Scripts\activate.bat" call "%ROOT%\.venv\Scripts\activate.bat"
set "FLASK_APP=backend:create_app"
pushd "%ROOT%"
python -m flask run --host=127.0.0.1 --port=5000
popd
if not defined NO_PAUSE pause
