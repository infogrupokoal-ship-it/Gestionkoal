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