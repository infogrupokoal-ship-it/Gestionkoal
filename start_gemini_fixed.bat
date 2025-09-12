@echo off
REM =====================================================
REM  KOAL - Start Gemini CLI in this project (Fixed)
REM  Requirements:
REM    - Node.js >= 20 (https://nodejs.org/)
REM    - npm on PATH (usually with Node.js)
REM  Behavior:
REM    - Checks Node/npm
REM    - Finds global npm bin and gemini.cmd (if installed)
REM    - If not installed, installs @google/gemini-cli globally
REM    - If still not present, falls back to: npx @google/gemini-cli@latest
REM    - Ensures GEMINI.md exists with project context
REM    - Runs Gemini CLI inside this project directory
REM =====================================================

setlocal enableextensions enabledelayedexpansion
title Gemini CLI - Gestionkoal
cd /d "%~dp0"

echo [1/8] Checking Node.js...
where node >NUL 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js no encontrado. Instala LTS (>= 20) desde https://nodejs.org/ y vuelve a intentarlo.
  pause
  exit /b 1
)

echo [2/8] Checking npm...
where npm >NUL 2>&1
if errorlevel 1 (
  echo [ERROR] npm no encontrado. Reinstala Node.js asegurando que npm quede en PATH.
  pause
  exit /b 1
)

echo [3/8] Localizando carpeta global de npm (npm bin -g)...
for /f "delims=" %%G in ('npm bin -g') do set "NPM_GLOBAL_BIN=%%G"
if not exist "%NPM_GLOBAL_BIN%" (
  echo [WARN] No se pudo obtener la carpeta global de npm. Continuando con NPX si es necesario.
)

echo [4/8] Buscando comando gemini instalado globalmente...
set "GEMINI_EXE="
if exist "%NPM_GLOBAL_BIN%\gemini.cmd" set "GEMINI_EXE=%NPM_GLOBAL_BIN%\gemini.cmd"
if not defined GEMINI_EXE (
  where gemini >NUL 2>&1 && for /f "delims=" %%P in ('where gemini') do set "GEMINI_EXE=%%P"
)

if not defined GEMINI_EXE (
  echo    Gemini CLI no encontrado globalmente. Instalando: npm install -g @google/gemini-cli
  call npm install -g @google/gemini-cli
  REM Reintentar deteccion
  for /f "delims=" %%G in ('npm bin -g') do set "NPM_GLOBAL_BIN=%%G"
  if exist "%NPM_GLOBAL_BIN%\gemini.cmd" set "GEMINI_EXE=%NPM_GLOBAL_BIN%\gemini.cmd"
)

echo [5/8] Variables de entorno del proyecto...
if "%FLASK_APP%"=="" set "FLASK_APP=app.py"
if "%DB_PATH%"=="" set "DB_PATH=database.db"
if "%UPLOAD_FOLDER%"=="" set "UPLOAD_FOLDER=uploads"
set "GEMINI_PROJECT=%cd%"
echo     FLASK_APP=%FLASK_APP%
echo     DB_PATH=%DB_PATH%
echo     UPLOAD_FOLDER=%UPLOAD_FOLDER%
echo     GEMINI_PROJECT=%GEMINI_PROJECT%

echo [6/8] Asegurando contexto GEMINI.md...
if not exist "GEMINI.md" (
  > "GEMINI.md" echo # Proyecto Gestionkoal - Contexto para Gemini CLI
  >> "GEMINI.md" echo Ruta del proyecto: %GEMINI_PROJECT%
  >> "GEMINI.md" echo Instrucciones: Edita solo app.py, templates\, static\, schema.sql y requirements.txt. No toques .venv\, uploads\, database.db.
  >> "GEMINI.md" echo SQL: usa "?" y _execute_sql(..., is_sqlite=is_sqlite).
)

echo [7/8] Lanzando Gemini CLI en esta carpeta...
if defined GEMINI_EXE (
  echo    Usando GEMINI_EXE=%GEMINI_EXE%
  "%GEMINI_EXE%"
) else (
  echo    Usando NPX fallback: npx @google/gemini-cli@latest
  npx @google/gemini-cli@latest
)

echo [8/8] Proceso de Gemini finalizado o ventana cerrada.
echo     Si no se abrio, revisa los mensajes de arriba y prueba manualmente:
echo       npx @google/gemini-cli@latest
pause
endlocal
