@echo off
REM Diagnóstico del entorno del proyecto
setlocal
set LOG=diagnostico_project.log
echo [i] Generando %LOG% ...

> "%LOG%" (
  echo === ENTORNO ===
  echo Fecha: %DATE% %TIME%
  echo Carpeta: %CD%
  echo.

  echo === PYTHON ===
  where python
  echo.
  echo -- python --version --
  python --version 2>&1
  echo.

  echo === VENV ===
  if exist venv (
    echo venv existe.
  ) else (
    echo venv NO existe.
  )
  echo.

  echo === PIP FREEZE (si hay venv) ===
  if exist venv (
    call venv\Scripts\activate
    pip --version
    pip freeze
  ) else (
    echo (sin venv)
  )
  echo.

  echo === DETECCIÓN FLASK_APP ===
  call 01_detect_flask_app.bat
  if errorlevel 1 (
    echo [!] No detectado automaticamente.
  ) else (
    echo FLASK_APP=%FLASK_APP%
  )
  echo.

  echo === IMPORT TEST ===
  if defined FLASK_APP (
    for /f "tokens=1,2 delims=:" %%a in ("%FLASK_APP%") do (
      set MOD=%%a
      set FACT=%%b
    )
    echo Intentando 'python -c "import %MOD% as m; print(m.__file__)"'...
    python -c "import %MOD% as m; print(m.__file__)" 2>&1
  ) else (
    echo Sin FLASK_APP, no se puede testear import.
  )
  echo.

  echo === FLASK CLI VERSION ===
  if exist venv (
    flask --version 2>&1
  ) else (
    echo (sin venv)
  )
  echo.
)

echo [✓] Hecho. Revisa %LOG% y compárteme lo importante si sigue fallando.
pause
endlocal
