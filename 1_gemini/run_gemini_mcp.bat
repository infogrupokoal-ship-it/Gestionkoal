@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
set "ROOT=%~dp0.."
echo [START] _gemini\run_gemini_mcp (ROOT=%ROOT%)
if exist "%~dp0env.local.bat" call "%~dp0env.local.bat"
if exist "%ROOT%\env.local.bat" call "%ROOT%\env.local.bat"
if exist "%ROOT%\.venv\Scripts\activate.bat" call "%ROOT%\.venv\Scripts\activate.bat"
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
for /f "tokens=1-3 delims=/.- " %%a in ("%date%") do (set "YYYY=%%c" & set "MM=%%b" & set "DD=%%a")
for /f "tokens=1-3 delims=:." %%a in ("%time%") do (set "HH=%%a" & set "NN=%%b" & set "SS=%%c")
set "HH=0%HH%" & set "HH=%HH:~-2%"
set "DATESTAMP=%YYYY%%MM%%DD%_%HH%%NN%%SS%"
set "SESSION_LOG=%LOG_DIR%\session_%DATESTAMP%.log"
set "GEMINI_CMD=" & for /f "usebackq delims=" %%L in ("%~dp0gemini_cmd.conf") do if not defined GEMINI_CMD set "GEMINI_CMD=%%L"
if not defined GEMINI_CMD set "GEMINI_CMD=gemini chat --mcp --verbose"
for /f "usebackq tokens=* delims=" %%L in ("%~dp0mcp_servers.conf") do (
  set "LINE=%%L"
  if not "!LINE!"=="" if /i not "!LINE:~0,1!"=="#" (
    echo [MCP] %%L
    start "MCP" cmd /k "%%L"
  )
)
echo [*] Lanzando Gemini: %GEMINI_CMD%
call %GEMINI_CMD%
if not defined NO_PAUSE pause
