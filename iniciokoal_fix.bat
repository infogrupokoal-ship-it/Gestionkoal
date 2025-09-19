@echo off
REM ===============================================================
REM  INICIO KOAL (FIX) - sin "activate", usando venv\Scripts\python
REM  Evita el error "No se esperaba ... en este momento."
REM ===============================================================
setlocal ENABLEDELAYEDEXPANSION
title Koal Launcher (FIX)

REM --- Directorio del proyecto ---
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

REM --- Config ---
set "FLASK_APP=backend:create_app"
set "HOST_DEV=127.0.0.1"
set "PORT_DEV=5000"
set "RENDER_URL=https://gestion-koal.onrender.com"
set "GIT_REMOTE=origin"

echo ============================================
echo   Grupo Koal - Gestion Avisos (FIX)
echo ============================================
echo [Dir] %PROJECT_DIR%
echo [FLASK_APP] %FLASK_APP%
echo.

REM --- Python / venv ---
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul || (echo [x] No se encontro Python en PATH. Instala Python. & pause & exit /b 1)
)

if not exist "venv\Scripts\python.exe" (
  echo [i] Creando entorno virtual...
  py -3 -m venv venv || python -m venv venv
)

REM --- Asegurar pip y requirements ---
echo [i] Actualizando pip...
"venv\Scripts\python" -m pip install --upgrade pip

if exist requirements.txt (
  echo [i] Instalando requirements.txt (puede tardar)...
  "venv\Scripts\python" -m pip install -r requirements.txt
) else (
  echo [!] No hay requirements.txt. Continuo.
)

REM --- init-db ---
echo [i] Inicializando base de datos...
"venv\Scripts\python" -m flask --app "%FLASK_APP%" init-db

REM --- Git push (Render) ---
where git >nul 2>nul
if not errorlevel 1 (
  echo [i] Preparando commit y push a %GIT_REMOTE%...
  git add -A
  git commit -m "Auto update via Koal FIX" || echo [i] Nada que commitear.
  git push %GIT_REMOTE% || echo [!] No se pudo hacer push (revisa remoto/credenciales).
) else (
  echo [!] Git no esta en PATH; saltando push.
)

REM --- Limpiar caches y puerto ---
echo [i] Limpiando __pycache__ ...
for /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"

echo [i] Cerrando proceso que use el puerto %PORT_DEV% (si lo hay)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTENING ^| findstr ":%PORT_DEV% " 2^>nul') do (
  echo [i] Matando PID %%p en puerto %PORT_DEV% ...
  taskkill /F /PID %%p >nul 2>&1
)

REM --- Detectar GEMINI_API_KEY (Usuario) ---
if not defined GEMINI_API_KEY (
  for /f "usebackq tokens=2,*" %%A in (`powershell -NoP -C "[Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User') ^| %{ 'VAL: ' + $_ }"`) do (
    if "%%A"=="VAL:" set "GEMINI_API_KEY=%%B"
  )
)

REM --- Ventana 1: Gemini CLI (solo si hay API key) ---
if defined GEMINI_API_KEY (
  start "Gemini CLI (Proyecto)" cmd /k "cd /d %PROJECT_DIR% && call venv\Scripts\activate && echo [i] GEMINI listo. Usa: gemini --help  ^&^& echo."
) else (
  echo [!] Sin GEMINI_API_KEY. No se abre la ventana de Gemini.
)

REM --- Ventana 2: Servidor local con flask (sin activate) ---
start "KOAL Local DEV" cmd /k "cd /d %PROJECT_DIR% && echo [i] Lanzando Flask DEV en http://%HOST_DEV%:%PORT_DEV%/ && venv\Scripts\python -m flask --app %FLASK_APP% run --host=%HOST_DEV% --port=%PORT_DEV%"

REM --- Ventana 3: Monitor de Render ---
set "TEST_PS=powershell -NoP -C "$r='%RENDER_URL%'; Write-Host '[i] Comprobando ' $r; while($true){ try{ $res=Invoke-WebRequest -Uri $r -UseBasicParsing -TimeoutSec 10; Write-Host (Get-Date).ToString('u') ' STATUS ' $res.StatusCode; if($res.StatusCode -eq 200){ Start-Process $r; Start-Sleep -Seconds 10}; } catch { Write-Host (Get-Date).ToString('u') ' ERROR '; } Start-Sleep -Seconds 5 }""
start "KOAL Internet (Render test)" cmd /k %TEST_PS%

REM --- Abrir navegadores ---
start "" "http://%HOST_DEV%:%PORT_DEV%/"
start "" "%RENDER_URL%"

echo.
echo [✓] Lanzado: Local + (Gemini si procede) + Monitor Render
echo [i] Si ves otra vez un 'parpadeo', ejecuta desde una consola:
echo     1) Abrir CMD
echo     2) cd "%PROJECT_DIR%"
echo     3) iniciokoal_fix.bat
echo.
pause
