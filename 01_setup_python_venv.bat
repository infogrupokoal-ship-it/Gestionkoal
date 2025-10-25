@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
set "ROOT=%~dp0.."
echo [START] 01_setup_python_venv (ROOT=%ROOT%)
if exist "%ROOT%\.venv\Scripts\activate.bat" call "%ROOT%\.venv\Scripts\activate.bat"
py -3 -m venv "%ROOT%\.venv"
if not exist "%ROOT%\.venv\Scripts\activate.bat" (
  echo [!] No se pudo crear el venv en %ROOT%\.venv
  if not defined NO_PAUSE pause
  exit /b 1
)
call "%ROOT%\.venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if exist "%ROOT%\requirements.txt" (
  pip install -r "%ROOT%\requirements.txt"
) else (
  echo [!] No existe requirements.txt en %ROOT%
)
if not defined NO_PAUSE pause
