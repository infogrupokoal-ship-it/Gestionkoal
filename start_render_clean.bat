@echo off
REM =======================================================
REM  Render deploy helper (clean output, robust file writes)
REM =======================================================

cd /d "%~dp0"

echo === 1) Ensuring Procfile ===
powershell -NoProfile -Command "$content = 'web: python run_waitress.py'; if (-not (Test-Path 'Procfile')) { Set-Content -Path 'Procfile' -Value $content -Encoding UTF8 }"

echo === 2) Writing render.yaml ===
powershell -NoProfile -Command "$content = @'
services:
  - type: web
    name: gestion-avisos
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python run_waitress.py
    envVars:
      - key: DB_PATH
        value: /var/data/database.db
      - key: UPLOAD_FOLDER
        value: /var/data/uploads
    disks:
      - name: data
        mountPath: /var/data
'@; Set-Content -Path 'render.yaml' -Value $content -Encoding UTF8"

echo === 3) Writing README_RENDER.md ===
powershell -NoProfile -Command "$content = @'
# Deploy en Render - Gestion Avisos

## Opción A: SQLite + Disk (recomendada para empezar)
1. Conecta tu repo a Render (New Web Service).
2. Asegúrate de estos campos:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_waitress.py`
3. Monta un **Disk** en `/var/data` (mínimo 1 GB).
4. Variables de entorno:
   - `DB_PATH=/var/data/database.db`
   - `UPLOAD_FOLDER=/var/data/uploads`
5. Tras el primer deploy, abre **Shell** (Render) y ejecuta:
   - `FLASK_APP=app.py flask init-db`

## Opción B: Postgres
1. Crea un servicio **Postgres** y copia la `DATABASE_URL` al servicio web.
2. En `requirements.txt` (para el servidor) agrega: `psycopg2-binary==2.9.9`
3. El código detecta `DATABASE_URL` y usa Postgres automáticamente.
4. Ejecuta `FLASK_APP=app.py flask init-db` en la Shell de Render.

## Notas
- El sistema de archivos de Render es efímero sin Disk. Usa Disk o Postgres.
- Para cargas de ficheros, asegura `UPLOAD_FOLDER` en el Disk.
- `Procfile` debe ser: `web: python run_waitress.py`
'@; Set-Content -Path 'README_RENDER.md' -Value $content -Encoding UTF8"

echo === 4) Summary ===
type Procfile
echo.
type render.yaml
echo.
echo [README_RENDER.md] creado.
echo Done.
pause