@echo off
REM ===============================================================
REM  Koal Launcher - Local + Render + (Gemini opcional)
REM  - Crea/activa venv, instala deps, init-db
REM  - git add/commit/push (origin) para redeploy en Render
REM  - Abre 3 ventanas: Gemini (si hay API), Flask local, Monitor Render
REM ===============================================================

setlocal ENABLEDELAYEDEXPANSION
title Koal Launcher

REM ---- RUTAS Y VARIABLES ----
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "FLASK_APP=backend:create_app"
set "HOST_DEV=127.0.0.1"
set "PORT_DEV=5000"
set "RENDER_URL=https://gestion-koal.onrender.com"
set "GIT_REMOTE=origin"

echo ============================================
echo   Grupo Koal - Gestion Avisos Launcher
echo ============================================
echo [Dir] %PROJECT_DIR%
echo [FLASK_APP] %FLASK_APP%
echo.

REM ---- PYTHON / VENV ----
where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul || (echo [x] No se encontro Python en PATH. Instala Python y vuelve. & pause & exit /b 1)
)

if not exist "venv" (
  echo [i] Creando entorno virtual...
  py -3 -m venv venv || python -m venv venv
)
echo [i] Activando venv...
call "venv\Scripts\activate.bat"

REM ---- DEPENDENCIAS ----
if exist requirements.txt (
  echo [i] Instalando dependencias de requirements.txt (puede tardar)...
  pip install -r requirements.txt
) else (
  echo [!] No hay requirements.txt. Continuo.
)

REM ---- INIT DB ----
echo [i] Inicializando base de datos (flask init-db)...
flask --app "%FLASK_APP%" init-db

REM ---- GIT PUSH (Render) ----
where git >nul 2>nul
if not errorlevel 1 (
  echo [i] Preparando commit y push a %GIT_REMOTE% ...
  git add -A
  git commit -m "Auto update via Koal Launcher" || echo [i] Nada que commitear.
  git push %GIT_REMOTE% || echo [!] No se pudo hacer push (comprueba remoto/credenciales).
) else (
  echo [!] Git no esta instalado o no esta en PATH. Saltando push a Render.
)

REM ---- LIMPIEZA Y REINICIO LOCAL ----
echo [i] Limpiando __pycache__ ...
for /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"

echo [i] Cerrando proceso que use el puerto %PORT_DEV% (si lo hay)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr LISTENING ^| findstr ":%PORT_DEV% " 2^>nul') do (
  echo [i] Matando PID %%p en puerto %PORT_DEV% ...
  taskkill /F /PID %%p >nul 2>&1
)

REM ---- DETECTAR GEMINI_API_KEY (si existe en entorno de Usuario) ----
if not defined GEMINI_API_KEY (
  for /f "usebackq tokens=2,*" %%A in (`powershell -NoP -C "[Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User') ^| %{ 'VAL: ' + $_ }"`) do (
    if "%%A"=="VAL:" set "GEMINI_API_KEY=%%B"
  )
)

REM ---- VENTANA 1: GEMINI CLI (solo si hay clave) ----
if defined GEMINI_API_KEY (
  start "Gemini CLI (Proyecto)" cmd /k "cd /d %PROJECT_DIR% && call venv\Scripts\activate && echo [i] GEMINI listo. Usa: gemini --help  ^&^& echo."
) else (
  echo [!] No hay GEMINI_API_KEY. No se abrira ventana de Gemini (el proyecto funciona igual).
)

REM ---- VENTANA 2: Servidor LOCAL Flask ----
start "KOAL Local DEV" cmd /k "cd /d %PROJECT_DIR% && call venv\Scripts\activate && set FLASK_ENV=development && set FLASK_DEBUG=1 && echo [i] Lanzando Flask DEV en http://%HOST_DEV%:%PORT_DEV%/ && flask --app %FLASK_APP% run --host=%HOST_DEV% --port=%PORT_DEV%"

REM ---- VENTANA 3: Monitor de Render ----
set "TEST_PS=powershell -NoP -C "$r='%RENDER_URL%'; Write-Host '[i] Comprobando ' $r; while($true){ try{ $res=Invoke-WebRequest -Uri $r -UseBasicParsing -TimeoutSec 10; Write-Host (Get-Date).ToString('u') ' STATUS ' $res.StatusCode; if($res.StatusCode -eq 200){ Start-Process $r; Start-Sleep -Seconds 10}; } catch { Write-Host (Get-Date).ToString('u') ' ERROR '; } Start-Sleep -Seconds 5 }""
start "KOAL Internet (Render test)" cmd /k %TEST_PS%

REM ---- Abrir navegadores ----
start "" "http://%HOST_DEV%:%PORT_DEV%/"
start "" "%RENDER_URL%"

echo.
echo [✓] Todo lanzado: Local + (Gemini si procede) + Monitor Render
echo [i] Si al hacer doble clic solo parpadea, ejecuta este archivo desde CMD:
echo     1) Abrir CMD
echo     2) cd "%PROJECT_DIR%"
echo     3) koal_launcher.bat
echo.
pause
