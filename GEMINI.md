# Proyecto Gestionkoal — Contexto para Gemini CLI
Fecha: 2025-09-12 19:52

## Instrucciones para el agente
- Trabaja exclusivamente en `C:\proyecto\gestion_avisos`.
- Edita solo: `app.py`, `templates\`, `static\`, `schema.sql`, `requirements.txt`.
- NO toques: `.venv\`, `uploads\`, `database.db`.
- SQL: usa `?` como placeholder; llama a `_execute_sql(..., is_sqlite=is_sqlite)`.
- Resume tus cambios con archivos y lineas afectadas.

## Objetivo inmediato
- Verificar login con usuarios de ejemplo (`password123`).
- Revisar formularios (trabajos/tareas) y seeds de base de datos.
- Preparar despliegue en Render (Disk) y guiar `flask init-db`.

## Datos utiles
- Repo GitHub: https://github.com/infogrupokoal-ship-it/Gestionkoal.git
- Variables locales: `DB_PATH=database.db`, `UPLOAD_FOLDER=uploads`, `FLASK_APP=app.py`
