@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Gemini + MCP Orchestrator (Windows, Gestionkoal)

set "VENV_DIR=.venv"
set "MCP_ROOT=%~dp0"
set "CFG_DIR=%~dp0"
set "SERVERS_FILE=%CFG_DIR%mcp_servers.conf"
set "GEMINI_CMD_FILE=%CFG_DIR%gemini_cmd.conf"
if not defined DEBUG_RUN set "DEBUG_RUN=0"
set "STARTUP_DELAY=2"
set "LOG_DIR=%~dp0logs"
set "ENV_LOCAL=%~dp0env.local.bat"

if exist "%ENV_LOCAL%" call "%ENV_LOCAL%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

for /f "tokens=1-3 delims=/.- " %%a in ("%date%") do (set "YYYY=%%c" & set "MM=%%b" & set "DD=%%a")
for /f "tokens=1-3 delims=:." %%a in ("%time%") do (set "HH=%%a" & set "NN=%%b" & set "SS=%%c")
set "HH=0%HH%" & set "HH=%HH:~-2%"
set "DATESTAMP=%YYYY%%MM%%DD%_%HH%%NN%%SS%"
set "SESSION_LOG=%LOG_DIR%\session_%DATESTAMP%.log"

call :log "=== Gemini + MCP Orchestrator - %DATE% %TIME% ==="

if exist "%~dp0..\env.local.bat" call "%~dp0..\env.local.bat"

if exist "%~dp0..\..\.venv\Scripts\activate.bat" (
  call :log "Activando venv (.venv) raíz si existe"
  call "%~dp0..\..\.venv\Scripts\activate.bat"
)

call :check_tool node
call :check_tool npx
call :check_tool python
call :check_tool gemini
call :check_tool uv

set "GEMINI_CMD="
if exist "%GEMINI_CMD_FILE%" (
  for /f "usebackq delims=" %%L in ("%GEMINI_CMD_FILE%") do if not defined GEMINI_CMD set "GEMINI_CMD=%%L"
)
if not defined GEMINI_CMD set "GEMINI_CMD=gemini chat --mcp --verbose"

if not exist "%SERVERS_FILE%" (
  call :log "ERROR: mcp_servers.conf no encontrado: %SERVERS_FILE%"
  goto :LAUNCH_GEMINI
)

set "SERVER_COUNT=0"
for /f "usebackq tokens=* delims=" %%L in ("%SERVERS_FILE%") do (
  set "LINE=%%L"
  if not "!LINE!"=="" if /i not "!LINE:~0,1!"=="#" (
    set /a SERVER_COUNT+=1
    set "SERVER_NAME=server!SERVER_COUNT!"
    set "SERVER_CMD=!LINE!"
    call :start_server "!SERVER_NAME!" "!SERVER_CMD!"
  )
)

if "%SERVER_COUNT%"=="0" (
  call :log "WARNING: No hay MCP definidos."
) else (
  call :log "Lanzados %SERVER_COUNT% MCP(s)."
)

call :sleep %STARTUP_DELAY%

:LAUNCH_GEMINI
call :log "Iniciando Gemini: %GEMINI_CMD%"
call %GEMINI_CMD%
set "RET=%ERRORLEVEL%"
call :log "Gemini exit code: %RET%"
goto :eof

:start_server
setlocal EnableDelayedExpansion
set "NAME=%~1"
set "CMD=%~2"
set "OUT_LOG=%LOG_DIR%\%NAME%_%DATESTAMP%.log"
call :log "Iniciando MCP [%NAME%]: %CMD%"
if "%DEBUG_RUN%"=="1" (
  call :log "DEBUG_RUN=1 -> foreground"
  pushd "%MCP_ROOT%"
  call %CMD% 1>>"%OUT_LOG%" 2>&1
  popd
) else (
  pushd "%MCP_ROOT%"
  start "MCP - %NAME%" cmd /k "%CMD% 1>>\"%OUT_LOG%\" 2>>&1"
  popd
)
endlocal & goto :eof

:check_tool
where %1 >nul 2>&1
if errorlevel 1 (
  call :log "WARN: '%~1' no está en PATH."
) else (
  for /f "usebackq tokens=*" %%v in (`%1 --version 2^>^&1`) do (
    call :log "%~1 version: %%v"
    goto :eof
  )
)
goto :eof

:log
echo %~1
>>"%SESSION_LOG%" echo %date% %time% - %~1
goto :eof

:sleep
setlocal
set "SECS=%~1"
if not defined SECS set "SECS=1"
powershell -NoProfile -Command "Start-Sleep -Seconds %SECS%" >nul 2>&1
endlocal & goto :eof
