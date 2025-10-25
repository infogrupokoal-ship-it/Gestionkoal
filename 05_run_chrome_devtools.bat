@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
set "ROOT=%~dp0.."
echo [START] 05_run_chrome_devtools
set "CHROME_EXE="
for %%P in (
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do (
  if exist %%~P set "CHROME_EXE=%%~P"
)
if not defined CHROME_EXE (
  echo [!] No se encontró chrome.exe en rutas comunes. Intento PATH...
  start "" chrome --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_mcp_9222" --new-window "about:blank"
  if not defined NO_PAUSE pause
  exit /b 0
)
echo [*] Lanzando Chrome (DevTools 9222)
start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_mcp_9222" --new-window "about:blank"
if not defined NO_PAUSE pause
