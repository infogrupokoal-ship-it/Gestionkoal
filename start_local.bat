@echo off
setlocal ENABLEEXTENSIONS

REM ===== Proyecto: Gestión de Avisos (Windows) =====
REM Uso:
REM   start_local.bat [backend:create_app]
REM   (Si tu fábrica de app NO es backend:create_app, pásala como argumento)
REM   Ej.: start_local.bat app:create_app

set APP_MODULE=backend:create_app
if not "%~1"=="" set APP_MODULE=%~1

REM Crear venv si no existe
if not exist "venv" (
  echo [+] Creando entorno virtual...
  py -3 -m venv venv
)

echo [+] Activando entorno virtual...
call "venv\Scripts\activate"

REM Instalar dependencias si hay requirements.txt
if exist "requirements.txt" (
  echo [+] Instalando dependencias de requirements.txt ...
  pip install --upgrade pip
  pip install -r requirements.txt
) else (
  echo [!] No se encontró requirements.txt. Continúo...
)

echo.
echo Listo. Variables configuradas para desarrollo.
echo   APP_MODULE=%APP_MODULE%
echo.
echo Comandos útiles:
echo   init_db.bat          -> Inicializa/crea la base de datos (si tu app lo soporta)
echo   run_dev.bat          -> Arranca el servidor Flask en http://127.0.0.1:5000
echo.
echo Si quieres cambiar el módulo de la app:  start_local.bat app:create_app
echo.

exit /b 0
