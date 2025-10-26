@echo off
REM ============================================================
REM  start_prod_local.bat  —  “Render local” with Docker
REM  Requisitos: Docker Desktop
REM  Uso:
REM     start_prod_local.bat              (build & run)
REM     start_prod_local.bat --rebuild    (forzar rebuild)
REM     start_prod_local.bat --stop       (detener y limpiar)
REM     start_prod_local.bat --logs       (mostrar logs y salir)
REM ============================================================

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM --- Config por defecto (puedes cambiar nombres/puertos si quieres)
set IMAGE_NAME=gestionkoal
set CONTAINER_NAME=gestionkoal_web
REM Puerto externo Windows -> Puerto interno contenedor ($PORT en Render)
if not defined PORT set PORT=5000
set HOST_PORT=%PORT%
set CONTAINER_PORT=5000

REM Secret mínimo para Flask
if not defined SECRET_KEY set SECRET_KEY=local-dev-secret

REM Directorio de instancia (persistencia de SQLite y otros)
set INSTANCE_DIR=%CD%\instance
if not exist "%INSTANCE_DIR%" (
  echo [+] Creando carpeta de instancia: "%INSTANCE_DIR%"
  mkdir "%INSTANCE_DIR%" >nul 2>&1
)

REM --- Helpers
for %%A in (%*) do (
  if /I "%%~A"=="--stop" goto :STOP
  if /I "%%~A"=="--logs" goto :LOGS
  if /I "%%~A"=="--rebuild" set FORCE_REBUILD=1
)

REM --- Verifica Docker
where docker >nul 2>&1
if errorlevel 1 (
  echo [!] Docker no encontrado. Instala Docker Desktop y reintenta.
  exit /b 1
)

REM --- Limpia contenedor previo si está corriendo
for /f "tokens=*" %%i in ('docker ps -aq --filter "name=%CONTAINER_NAME%"') do set OLD_ID=%%i
if defined OLD_ID (
  echo [i] Deteniendo/eliminando contenedor previo "%CONTAINER_NAME%"...
  docker rm -f %CONTAINER_NAME% >nul 2>&1
)

REM --- Construye imagen
if defined FORCE_REBUILD (
  echo [*] Rebuild forzado de la imagen "%IMAGE_NAME%"...
  docker build --no-cache -t %IMAGE_NAME% .
) else (
  echo [*] Construyendo imagen "%IMAGE_NAME%"...
  docker build -t %IMAGE_NAME% .
)
if errorlevel 1 (
  echo [!] Error durante docker build.
  exit /b 1
)

REM --- Ejecuta contenedor en “modo Render”
REM     - Parametriza puerto por variable, usuario no-root ya viene en Dockerfile
REM     - Monta /instance para persistir DB igual que en Render
echo [*] Lanzando contenedor "%CONTAINER_NAME%" en http://127.0.0.1:%HOST_PORT% ...
docker run --name %CONTAINER_NAME% ^
  -p %HOST_PORT%:%CONTAINER_PORT% ^
  -e PORT=%CONTAINER_PORT% ^
  -e SECRET_KEY=%SECRET_KEY% ^
  -e FLASK_APP=backend:create_app ^
  -e FLASK_ENV=production ^
  -e WHATSAPP_DRY_RUN=1 ^
  -e GEMINI_API_KEY=demo ^
  -v "%INSTANCE_DIR%:/app/instance" ^
  -d %IMAGE_NAME%
if errorlevel 1 (
  echo [!] Error al iniciar el contenedor.
  exit /b 1
)

echo [+] Contenedor "%CONTAINER_NAME%" lanzado en segundo plano. Puedes acceder en http://127.0.0.1:%HOST_PORT%/
echo     Para ver logs:         start_prod_local.bat --logs
echo     Para detener servicio: start_prod_local.bat --stop
exit /b 0

:HEALTH_OK
echo [+] Salud OK. Servicio listo: http://127.0.0.1:%HOST_PORT%/
echo     Endpoint healthz:      http://127.0.0.1:%HOST_PORT%/healthz
echo     Para ver logs:         start_prod_local.bat --logs
echo     Para detener servicio: start_prod_local.bat --stop
exit /b 0


:LOGS
REM Muestra logs (follow) si el contenedor existe
for /f "tokens=*" %%i in ('docker ps -aq --filter "name=%CONTAINER_NAME%"') do set CID=%%i
if not defined CID (
  echo [!] No hay contenedor "%CONTAINER_NAME%" activo/creado.
  exit /b 1
)
echo [*] Mostrando logs (Ctrl+C para salir)...
docker logs -f %CONTAINER_NAME%
exit /b 0


:STOP
for /f "tokens=*" %%i in ('docker ps -aq --filter "name=%CONTAINER_NAME%"') do set SID=%%i
if not defined SID (
  echo [i] No hay contenedor "%CONTAINER_NAME%" para detener.
  exit /b 0
)
echo [*] Deteniendo y eliminando contenedor "%CONTAINER_NAME%"...
docker rm -f %CONTAINER_NAME% >nul 2>&1
echo [+] Contenedor eliminado.
exit /b 0
