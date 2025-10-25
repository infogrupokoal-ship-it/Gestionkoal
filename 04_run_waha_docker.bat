@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
set "ROOT=%~dp0.."
echo [START] 04_run_waha_docker
where docker >nul 2>&1 || (echo [!] Docker no encontrado & if not defined NO_PAUSE pause & exit /b 1)
if not defined WAHA_PORT set WAHA_PORT=3000
for /f "tokens=*" %%i in ('docker ps -a --filter "name=waha" --format "{{.Names}}"' ) do set EXISTS=1
if defined EXISTS (docker start waha) else (docker run -d --name waha -p %WAHA_PORT%:3000 devlikeapro/waha:latest)
echo [+] WAHA en http://localhost:%WAHA_PORT%/
if not defined NO_PAUSE pause
