import re
import os

file_path = "C:\\Users\\info\\OneDrive\\Escritorio\\gestion_avisos\\app.py"

# Asegúrate de que el archivo existe antes de intentar leerlo
if not os.path.exists(file_path):
    print(f"Error: El archivo no se encontró en {file_path}")
    exit()

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    # setup_new_database (SQLite)
    (r"(?P<indent>\\s*)(?P<var>admin_role_id) = cursor.execute(\"SELECT id FROM roles WHERE name = 'Admin'\").fetchone()["id"]",