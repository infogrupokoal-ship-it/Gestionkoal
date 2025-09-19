@echo off
REM Tries to detect the FLASK_APP entry automatically.
REM Sets FLASK_APP and returns with exit code 0 if detected, 1 otherwise.
setlocal

set CANDIDATES=backend:create_app backend:app app:create_app app:app main:create_app main:app

for %%M in (%CANDIDATES%) do (
  for /f "tokens=1 delims=:" %%A in ("%%M") do (
    set FILE=%%A
  )
  if exist %%FILE%%\__init__.py (
    set FLASK_APP=%%M
    echo [i] Using FLASK_APP=%%M
    endlocal & set FLASK_APP=%FLASK_APP% & exit /b 0
  )
  if exist %%FILE%%.py (
    set FLASK_APP=%%M
    echo [i] Using FLASK_APP=%%M
    endlocal & set FLASK_APP=%FLASK_APP% & exit /b 0
  )
)

echo [x] Could not auto-detect FLASK_APP. Please edit 01_detect_flask_app.bat to set it manually.
endlocal
exit /b 1
