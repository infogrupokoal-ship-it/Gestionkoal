@echo off
REM =======================================================
REM  Render deploy helper (local packaging steps for Windows)
REM  This does NOT deploy by itself; it prepares the repo.
REM =======================================================

cd /d "%~dp0"

echo === 1) Ensuring Procfile exists ===
if not exist "Procfile" (
  echo web: python run_waitress.py> Procfile
  echo Created Procfile with: web: python run_waitress.py
) else (
  echo Procfile already present.
)

echo === 2) Creating render.yaml (service + disk SQLite) ===
> render.yaml echo services:
>> render.yaml echo ^- type: web
>> render.yaml echo ^  name: gestion-avisos
>> render.yaml echo ^  env: python
>> render.yaml echo ^  plan: free
>> render.yaml echo ^  buildCommand: pip install -r requirements.txt
>> render.yaml echo ^  startCommand: python run_waitress.py
>> render.yaml echo ^  envVars:
>> render.yaml echo ^    - key: DB_PATH
>> render.yaml echo ^      value: /var/data/database.db
>> render.yaml echo ^    - key: UPLOAD_FOLDER
>> render.yaml echo ^      value: /var/data/uploads
>> render.yaml echo ^  disks:
>> render.yaml echo ^    - name: data
>> render.yaml echo ^      mountPath: /var/data

echo === 3) Creating README_RENDER.md with instructions ===
> README_RENDER.md echo # Deploy en Render - Gestion Avisos
>> README_RENDER.md echo
>> README_RENDER.md echo ## Opcion A: SQLite + Disk (recomendada para empezar)
>> README_RENDER.md echo 1. Conecta tu repo a Render (New Web Service).
>> README_RENDER.md echo 2. Asegurate de estos campos:
>> README_RENDER.md echo    - **Build Command**: ^`pip install -r requirements.txt^`
>> README_RENDER.md echo    - **Start Command**: ^`python run_waitress.py^`
>> README_RENDER.md echo 3. Monta un **Disk** en ^`/var/data^` (minimo 1 GB).
>> README_RENDER.md echo 4. Variables de entorno:
>> README_RENDER.md echo    - ^`DB_PATH=/var/data/database.db^`
>> README_RENDER.md echo    - ^`UPLOAD_FOLDER=/var/data/uploads^`
>> README_RENDER.md echo 5. Tras el primer deploy, abre shell ^(Render^) y ejecuta:
>> README_RENDER.md echo    - ^`FLASK_APP=app.py flask init-db^`
>> README_RENDER.md echo
>> README_RENDER.md echo ## Opcion B: Postgres
>> README_RENDER.md echo 1. Crea un servicio Postgres y copia la ^`DATABASE_URL^` al servicio web.
>> README_RENDER.md echo 2. En requirements.txt ^(para el servidor^) agrega: ^`psycopg2-binary==2.9.9^`
>> README_RENDER.md echo 3. El codigo detecta ^`DATABASE_URL^` y usa Postgres automaticamente.
>> README_RENDER.md echo 4. Ejecuta ^`FLASK_APP=app.py flask init-db^` en la shell de Render.
>> README_RENDER.md echo
>> README_RENDER.md echo ## Notas
>> README_RENDER.md echo - El sistema de archivos de Render es efimero sin Disk. Usa Disk o Postgres.
>> README_RENDER.md echo - Para cargas de ficheros, asegura ^`UPLOAD_FOLDER^` en el Disk.
>> README_RENDER.md echo - ^`Procfile^` debe ser: ^`web: python run_waitress.py^`

echo === 4) Show summary ===
type Procfile
echo.
type render.yaml
echo.
type README_RENDER.md
echo.
echo Done.
pause