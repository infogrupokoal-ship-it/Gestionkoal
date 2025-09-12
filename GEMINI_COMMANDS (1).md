# Gemini – Comandos / Prompts Útiles

## 1) Mensaje de arranque (copiar/pegar al abrir la IA)
Trabaja exclusivamente en C:\proyecto\gestion_avisos.
Edita solo app.py, templates\, static\, schema.sql y requirements.txt.
No toques .venv\, uploads\ ni database.db.
Usa siempre ? como placeholder SQL y pasa is_sqlite=is_sqlite en _execute_sql.
Resume tus cambios con rutas y líneas afectadas.
Si una edición falla por texto no único, muestra el fragmento exacto que encontraste.

## 2) Revisión y commits
- Antes de cambios grandes: “Crea checkpoint de Git” (yo haré `git add -A && git commit -m "Checkpoint..."`).
- Al terminar: “Resume cambios y puntos de prueba”.

## 3) Estándares en app.py
- Conexión: `get_db_connection()` detecta DATABASE_URL o DB_PATH.
- Cursores: usa `get_cursor(conn)`.
- SQL: escribe con `?` y llama `_execute_sql(cursor, sql, params, is_sqlite=is_sqlite)`.
- Nada de `with conn.cursor()` en SQLite; usa try/finally si es necesario.

## 4) Plantillas
- Añadir JS no intrusivo y sin romper Jinja.
- Mantener IDs únicos y usar `DOMContentLoaded`.

## 5) Evitar
- Rutas absolutas a OneDrive o C:\Users\...
- Cambiar `.gitignore`, `.venv/`, `uploads/`, `database.db`.
- Introducir `%s` en SQL sin pasar por el adaptador.
