@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 04_run_waha_docker - Gestionkoal
if exist "env.local.bat" call "env.local.bat"

where docker >nul 2>&1
if errorlevel 1 (
  echo [!] Docker no está en PATH. Instala/abre Docker Desktop.
  exit /b 1
)

if not defined WAHA_PORT set "WAHA_PORT=3000"

for /f "tokens=*" %%i in ('docker ps -a --filter "name=waha" --format "{{.Names}}"') do set "EXISTS=1"
if defined EXISTS (
  echo [*] Arrancando contenedor existente 'waha'...
  docker start waha
) else (
  echo [*] Creando contenedor 'waha' en puerto %WAHA_PORT%...
  docker run -d --name waha -p %WAHA_PORT%:3000 devlikeapro/waha:latest
)

echo [+] WAHA en http://localhost:%WAHA_PORT%/
