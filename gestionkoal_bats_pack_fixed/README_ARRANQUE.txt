README - Arranque y marcha (Gestionkoal)

Coloca esta carpeta en: C:\proyecto\gestion_avisos\

Scripts:
1) 01_setup_python_venv.bat  -> Crea/activa .venv e instala requirements.txt
2) 02_run_dev.bat            -> Flask dev en http://127.0.0.1:5000
3) 03_run_prod_like.bat      -> Waitress local (similar a Render)
4) 04_run_waha_docker.bat    -> Arranca WAHA (Docker) en puerto 3000
5) 05_run_chrome_devtools.bat-> Abre Chrome con --remote-debugging-port=9222 (MCP Chrome)
6) 06_run_all.bat            -> TODO en orden: venv -> migraciones -> WAHA -> Chrome -> Gemini+MCP -> Flask
7) open_logs.bat             -> Abre carpeta logs
10) 10_db_upgrade.bat        -> flask db upgrade
11) 10_db_downgrade.bat      -> flask db downgrade <revision>
12) 10_db_stamp.bat          -> flask db stamp <revision>

Claves locales (env.local.bat) ya incluyen:
- SECRET_KEY (segura generada)
- GEMINI_API_KEY (tu clave)
- GH_TOKEN (tu token)

Render (producción):
- Start: waitress-serve --host=0.0.0.0 --port=$PORT --call backend:create_app --threads=4
- Variables: SECRET_KEY, GEMINI_API_KEY, DATABASE_URL (si Postgres)
- Persistencia: usar carpeta instance/

Diagnóstico rápido:
- MCP: usar run_gemini_mcp_DEBUG.bat y revisar _gemini\logs\
- WAHA: Docker Desktop encendido y puerto 3000 libre
- Alembic: si falla, reintenta 10_db_upgrade.bat o consulta 10_db_downgrade/stamp
