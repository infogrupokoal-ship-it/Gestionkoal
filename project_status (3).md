# Estado del Proyecto — Gestionkoal (Gestión de Avisos)
**Fecha:** 2025-09-12 19:45  
**Ruta local (Windows):** `C:\proyecto\gestion_avisos`  
**Repo GitHub:** `https://github.com/infogrupokoal-ship-it/Gestionkoal.git`  
**Objetivo:** Ejecutar en local con SQLite y desplegar en Render (Disk), manteniendo compatibilidad con Postgres.

---

## 1) Resumen ejecutivo
- Proyecto fuera de OneDrive (menos bloqueos y mejor rendimiento).
- Código preparado para **SQLite** (local / Render Disk) y **Postgres** (Render) con `get_db_connection()`.
- Adaptador SQL: usar **`?`** en consultas; `_execute_sql(...)` adapta a SQLite/Postgres.
- Scripts de arranque:
  - **Producción local**: `start_local_fixed.bat` → lanza `waitress` (estable, como Render).
  - **Desarrollo**: `start_dev_fixed.bat` → `flask run` con **autoreload**.
- Archivos de despliegue listos: **Procfile**, **render.yaml**, **README_RENDER.md**.

---

## 2) Hecho (DONE)
- [x] Arreglo de `/login` y `user_loader` para SQLite/Postgres.
- [x] Unificación de placeholders con `_execute_sql()` y `get_cursor()`.
- [x] CLI `init-db` operativo (lee `schema.sql` por bloques).
- [x] `.gitignore` recomendado (`.venv/`, `database.db`, `uploads/`).
- [x] Guías locales (README_LOCAL.md) y **comandos para IA (Gemini)**.

---

## 3) Pendiente inmediato (TODO)
1. Verificar **login** con usuarios de ejemplo (`password123`).
2. Subir cambios a GitHub tras confirmar que arranca:
   ```powershell
   git add -A
   git commit -m "Arranque estable; login OK; guías y scripts"
   git push
   ```
3. Desplegar en Render (SQLite + Disk) y ejecutar en Shell:
   ```bash
   FLASK_APP=app.py flask init-db
   ```

---

## 4) Problemas conocidos y mitigación
- **psycopg2 (Windows/Py3.13)**: no instalar en local; usar SQLite. En Render+Postgres usar `psycopg2-binary`.
- **Herramientas Google (gaxios badRequest)**: desactivar si no se usan; si se usan, configurar credenciales/scopes correctos.
- **Cambios con waitress corriendo**: reiniciar servidor tras cambios. En desarrollo usar `start_dev_fixed.bat` (autoreload).
- **Rutas absolutas al usuario/OneDrive**: evitar; trabajar siempre en `C:\proyecto\gestion_avisos`.

---

## 5) Checklist de verificación
- [ ] `start_local_fixed.bat` o `start_dev_fixed.bat` levantan sin errores.
- [ ] `/login` permite entrar con usuarios de ejemplo.
- [ ] Subida/listado de archivos escribe en `UPLOAD_FOLDER`.
- [ ] `flask init-db` ejecutado en Render tras primer deploy.
- [ ] GitHub actualizado (`main` al día).

---

## 6) Variables de entorno útiles
- **Local (SQLite)**  
  `DB_PATH=database.db`  
  `UPLOAD_FOLDER=uploads`  
  `FLASK_APP=app.py`
- **Render (SQLite + Disk)**  
  `DB_PATH=/var/data/database.db`  
  `UPLOAD_FOLDER=/var/data/uploads`
- **Render (Postgres)**  
  `DATABASE_URL=postgres://...`

---

## 7) Flujo recomendado de trabajo
1. **Desarrollo** con `start_dev_fixed.bat` (autoreload).  
2. Confirmar que funciona → **commit & push** a GitHub.  
3. **Desplegar** en Render (Procfile + Disk + env vars).  
4. Ejecutar `flask init-db` en Shell de Render.  
5. Validar en URL pública.

---

## 8) Notas para IA local (Gemini)
- Directorio de trabajo: `C:\proyecto\gestion_avisos`.
- Editar solo: `app.py`, `templates/`, `static/`, `schema.sql`, `requirements.txt`.
- No editar: `.venv/`, `uploads/`, `database.db`.
- SQL: usar **`?`** como placeholder: `_execute_sql(cursor, sql, params, is_sqlite=is_sqlite)`.
- Tras cambios: si usas waitress, **reinicia**; si usas dev, autoreload aplica.
