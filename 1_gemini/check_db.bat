@echo off
echo [DB_CHECK] Cambiando al directorio del proyecto...
cd C:\proyecto\gestion_avisos

echo [DB_CHECK] Activando entorno virtual...
call .\.venv\Scripts\activate

echo [DB_CHECK] Estableciendo FLASK_APP...
set FLASK_APP=backend:create_app

echo [DB_CHECK] Limpiando log anterior...
if exist "C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log" del "C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log"

echo [DB_CHECK] Ejecutando 'flask db heads'...
flask db heads > C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log 2>&1

echo. >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log
echo ----- SEPARATOR ----- >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log
echo. >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log

echo [DB_CHECK] Ejecutando 'flask db current'...
flask db current >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log 2>&1

echo [DB_CHECK] Hecho. La salida esta en db_check.log.