@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d %~dp0
echo [START] 06_run_all
call 01_setup_python_venv.bat
call 10_db_upgrade.bat
start "WAHA" cmd /k "04_run_waha_docker.bat"
start "Chrome DevTools 9222" cmd /k "05_run_chrome_devtools.bat"
start "Gemini+MCP" cmd /k "run_gemini_mcp.bat"
start "Flask dev" cmd /k "02_run_dev.bat"
