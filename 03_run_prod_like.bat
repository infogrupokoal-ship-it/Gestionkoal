@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
set "ROOT=%~dp0.."
echo [START] 03_run_prod_like (ROOT=%ROOT%)
if exist "%ROOT%\.venv\Scripts\activate.bat" call "%ROOT%\.venv\Scripts\activate.bat"
pushd "%ROOT%"
waitress-serve --host=0.0.0.0 --port=5000 --call backend:create_app --threads=4
popd
if not defined NO_PAUSE pause
