@echo off
setlocal EnableExtensions EnableDelayedExpansion
title 06_run_all (Gestionkoal stack)

echo [*] 1) Entorno Python
call 01_setup_python_venv.bat || goto :end

echo [*] 2) Migraciones BD
call 10_db_upgrade.bat || goto :end

echo [*] 3) WAHA (Docker)
start "WAHA" cmd /k "04_run_waha_docker.bat"

echo [*] 4) Chrome DevTools (9222) para MCP
start "Chrome DevTools 9222" cmd /k "05_run_chrome_devtools.bat"

echo [*] 5) Gemini + MCP
start "Gemini+MCP" cmd /k "run_gemini_mcp.bat"

echo [*] 6) Backend (Flask dev) en nueva ventana
start "Flask dev" cmd /k "02_run_dev.bat"

echo [+] Todo lanzado. Deja abiertas:
echo    - "Flask dev" (o "Waitress" si usas 03_run_prod_like)
echo    - "Gemini+MCP" si usas el asistente IA
echo    - WAHA queda en Docker

:end
