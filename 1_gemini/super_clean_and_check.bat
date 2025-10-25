@echo off
echo [CLEAN AND CHECK] Cambiando al directorio del proyecto...
cd C:\proyecto\gestion_avisos

echo [CLEAN AND CHECK] Eliminando cache de Python (__pycache__)...
for /d /r . %%d in (__pycache__) do (if exist "%%d" rmdir /s /q "%%d")

echo [CLEAN AND CHECK] Forzando la sobreescritura del archivo jobs.py corregido...
copy /Y "C:\proyecto\gestion_avisos\1_gemini\analysis\jobs_super_fixed.py.txt" "C:\proyecto\gestion_avisos\backend\jobs.py"

echo [CLEAN AND CHECK] Activando entorno virtual...
call .\.venv\Scripts\activate

echo [CLEAN AND CHECK] Estableciendo FLASK_APP...
set FLASK_APP=backend:create_app

echo [CLEAN AND CHECK] Limpiando log anterior...
if exist "C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log" del "C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log"

echo [CLEAN AND CHECK] Ejecutando 'flask db heads'...
flask db heads > C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log 2>&1

echo. >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log
echo ----- SEPARATOR ----- >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log
echo. >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log

echo [CLEAN AND CHECK] Ejecutando 'flask db current'...
flask db current >> C:\proyecto\gestion_avisos\1_gemini\logs\db_check.log 2>&1

echo [CLEAN AND CHECK] Hecho. La salida esta en db_check.log.