@echo off
REM =====================================================
REM  KOAL - Start Gemini CLI in this project
REM  Requirements:
REM    - Node.js >= 20 (https://nodejs.org/)
REM    - NPM available in PATH
REM  What it does:
REM    1) Verifies Node & npm
REM    2) Installs Gemini CLI globally if missing
REM    3) Sets env vars for the project
REM    4) Launches 'gemini' inside the project directory
REM =====================================================

setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo [1/6] Checking Node.js...
where node >NUL 2>&1 || (
  echo [ERROR] Node.js no encontrado. Instala la version LTS (>= 20) desde https://nodejs.org/ e intenta de nuevo.
  pause
  exit /b 1
)

echo [2/6] Checking npm...
where npm >NUL 2>&1 || (
  echo [ERROR] npm no encontrado. Reinstala Node.js asegurando que npm quede en PATH.
  pause
  exit /b 1
)

echo [3/6] Checking Gemini CLI...
where gemini >NUL 2>&1
if errorlevel 1 (
  echo    Gemini CLI no instalado; instalando globalmente...
  call npm install -g @google/gemini-cli
  if errorlevel 1 (
    echo [WARN] Instalacion global fallo. Probando modo temporal con npx al iniciar.
    set "GEMINI_USE_NPX=1"
  )
)

echo [4/6] Seteando variables del proyecto...
if "%FLASK_APP%"=="" set "FLASK_APP=app.py"
if "%DB_PATH%"=="" set "DB_PATH=database.db"
if "%UPLOAD_FOLDER%"=="" set "UPLOAD_FOLDER=uploads"
set "GEMINI_PROJECT=%cd%"
echo     FLASK_APP=%FLASK_APP%
echo     DB_PATH=%DB_PATH%
echo     UPLOAD_FOLDER=%UPLOAD_FOLDER%
echo     GEMINI_PROJECT=%GEMINI_PROJECT%

echo [5/6] Asegurando contexto GEMINI.md...
if not exist "GEMINI.md" (
  echo Creando GEMINI.md basico...
  > "GEMINI.md" echo # Proyecto Gestionkoal - Contexto para Gemini CLI
  >> "GEMINI.md" echo Ruta del proyecto: %GEMINI_PROJECT%
  >> "GEMINI.md" echo Instrucciones: Edita solo app.py, templates\, static\, schema.sql, requirements.txt. No toques .venv\, uploads\, database.db.
  >> "GEMINI.md" echo SQL: usa "?" y _execute_sql(..., is_sqlite=is_sqlite).
)

echo [6/6] Lanzando Gemini CLI en esta carpeta...
if "%GEMINI_USE_NPX%"=="1" (
  start cmd /k "cd /d %GEMINI_PROJECT% && npx https://github.com/google-gemini/gemini-cli"
) else (
  start cmd /k "cd /d %GEMINI_PROJECT% && gemini"
)

echo.
echo [OK] Se abrio una nueva ventana con Gemini CLI en esta carpeta.
echo     Consejos rapidos dentro de Gemini:
echo       /help, /tools, /memory, /stats
echo       Escribe: 'Analiza este repositorio y dime los siguientes pasos'
echo.
pause
endlocal
