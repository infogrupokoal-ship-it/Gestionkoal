@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM =========================================================
REM initdb.bat — Inicializa la base de datos Flask
REM Uso: Ejecutar en la carpeta raíz del proyecto (como Admin recomendado)
REM Hace:
REM   - Cambia a la carpeta del script
REM   - Usa venv\Scripts\python.exe si existe (si no, python del sistema)
REM   - Asegura PYTHONPATH=%CD% para que Python vea el paquete local
REM   - Crea instance\ y limpia locks de SQLite
REM   - Prueba varias rutas de FLASK_APP con create_app (backend/app/src.backend/gestion_avisos.backend)
REM   - Ejecuta: flask init-db
REM =========================================================

cd /d "%~dp0"

REM --- Elegir Python ---
set "PYTHON_EXE=venv\Scripts\python.exe"
if exist "%PYTHON_EXE%" (
  echo Usando Python del entorno virtual: %PYTHON_EXE%
) else (
  set "PYTHON_EXE=python"
  echo No se encontro venv\Scripts\python.exe, se usara: %PYTHON_EXE%
)

REM --- Asegurar que el paquete local es importable ---
set "PYTHONPATH=%CD%"

REM --- Preparar carpeta instance y limpiar locks ---
if not exist "instance" mkdir "instance" 2>nul
del /q "instance\*.sqlite-wal" 2>nul
del /q "instance\*.sqlite-shm" 2>nul
del /q "instance\*.sqlite-journal" 2>nul

REM --- Desactivar debugger/reloader por si acaso ---
set "FLASK_DEBUG=0"

REM === Probar rutas de app en orden ===
set "FLASK_APP="
echo.
echo === Probando FLASK_APP=backend:create_app ===
set "CANDIDATE=backend:create_app"
"%PYTHON_EXE%" -m flask --app "%CANDIDATE%" --help 1>nul 2>nul
if not errorlevel 1 (
  set "FLASK_APP=%CANDIDATE%"
  goto RUN_INIT_DB
)

echo.
echo === Probando FLASK_APP=app:create_app ===
set "CANDIDATE=app:create_app"
"%PYTHON_EXE%" -m flask --app "%CANDIDATE%" --help 1>nul 2>nul
if not errorlevel 1 (
  set "FLASK_APP=%CANDIDATE%"
  goto RUN_INIT_DB
)

echo.
echo === Probando FLASK_APP=src.backend:create_app ===
set "CANDIDATE=src.backend:create_app"
"%PYTHON_EXE%" -m flask --app "%CANDIDATE%" --help 1>nul 2>nul
if not errorlevel 1 (
  set "FLASK_APP=%CANDIDATE%"
  goto RUN_INIT_DB
)

echo.
echo === Probando FLASK_APP=gestion_avisos.backend:create_app ===
set "CANDIDATE=gestion_avisos.backend:create_app"
"%PYTHON_EXE%" -m flask --app "%CANDIDATE%" --help 1>nul 2>nul
if not errorlevel 1 (
  set "FLASK_APP=%CANDIDATE%"
  goto RUN_INIT_DB
)

echo.
echo [ERROR] No pude importar tu app Flask automaticamente.
echo - Asegurate de ejecutar este .bat en la carpeta RAIZ del proyecto.
echo - Verifica el nombre del paquete y que exista create_app().
echo - Prueba manualmente, por ejemplo:
echo     %PYTHON_EXE% -m flask --app "backend:create_app" --help
goto END_FAIL

:RUN_INIT_DB
echo.
echo Usando FLASK_APP=%FLASK_APP%
echo === Ejecutando: flask init-db ===
"%PYTHON_EXE%" -m flask --app "%FLASK_APP%" init-db
if errorlevel 1 (
  echo.
  echo [ERROR] init-db fallo o no existe.
  echo Posibles causas:
  echo   1) No registraste el comando en create_app():
  echo        from . import db
  echo        db.init_app(app)
  echo        db.register_commands(app)
  echo   2) Hay errores al importar modulos (revisa el traceback ejecutando --help sin redireccion):
  echo        %PYTHON_EXE% -m flask --app "%FLASK_APP%" --help
  echo   3) app.run() se ejecuta al importar (debe ir solo bajo if __name__ == "__main__":)
  goto END_FAIL
)

echo.
echo [OK] Base de datos inicializada. Revisa instance\*.sqlite
goto END_OK

:END_OK
echo.
echo Pulsa una tecla para salir...
pause >nul
exit /b 0

:END_FAIL
echo.
echo Pulsa una tecla para salir...
pause >nul
exit /b 1
