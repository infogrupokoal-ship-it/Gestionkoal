@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 01_setup_python_venv (Gestionkoal)
if exist "env.local.bat" call "env.local.bat"

echo [*] Creando/activando entorno virtual .venv...
py -3 -m venv .venv
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
) else (
  echo [!] No se encontró .venv\Scripts\activate.bat
  exit /b 1
)

python -m pip install --upgrade pip
if exist "requirements.txt" (
  pip install -r requirements.txt
) else (
  echo [!] No existe requirements.txt en esta carpeta.
)
echo [+] Entorno listo.
