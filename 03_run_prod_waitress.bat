@echo off
REM Run app locally with Waitress (production-like, no auto-reload)
REM Adjust APP_MODULE:function if needed.
setlocal
call 00_setup_venv.bat >nul

REM Try to detect module for waitress too
call 01_detect_flask_app.bat >nul
if errorlevel 1 (
  echo [!] Falling back to APP_MODULE guess: backend:app
  set APP_MODULE=backend:app
) else (
  REM Convert "pkg:create_app" to a small waitres callable using a shim
  for /f "tokens=1,2 delims=:" %%a in ("%FLASK_APP%") do (
    set PKG=%%a
    set FACTORY=%%b
  )
  if /i "%FACTORY%"=="create_app" (
    set APP_MODULE=%PKG%:app
    if not exist _waitress_shim.py (
      echo from %PKG% import create_app> _waitress_shim.py
      echo app = create_app()>> _waitress_shim.py
    )
    set APP_MODULE=_waitress_shim:app
  ) else (
    set APP_MODULE=%FLASK_APP%
  )
)

set PORT=8000
set HOST=0.0.0.0

echo [i] Activating venv...
call venv\Scripts\activate
echo [i] Installing waitress if needed...
pip install waitress

echo [i] Starting waitress-serve on %HOST%:%PORT% ...
start "" "http://127.0.0.1:%PORT%/"
python -m waitress --listen=%HOST%:%PORT% %APP_MODULE%
endlocal
