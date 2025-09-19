@echo off
REM Create and (optionally) update a local virtual environment
REM Usage: double-click or run from terminal in the project root.

setlocal enabledelayedexpansion
IF NOT EXIST venv (
  echo [i] Creating virtual environment...
  py -3 -m venv venv || python -m venv venv
) ELSE (
  echo [i] Virtual environment already exists.
)

echo [i] Upgrading pip...
call venv\Scripts\python -m pip install --upgrade pip

IF EXIST requirements.txt (
  echo [i] Installing dependencies from requirements.txt ...
  call venv\Scripts\pip install -r requirements.txt
) ELSE (
  echo [!] requirements.txt not found. Skipping dependency install.
)

echo [✓] Venv ready. To activate: call venv\Scripts\activate
endlocal
pause
