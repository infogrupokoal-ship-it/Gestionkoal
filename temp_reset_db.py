import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'gestion_avisos.sqlite')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'backend', 'schema.sql')

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

with open(SCHEMA_PATH) as f:
    sql_script = f.read()

for statement in sql_script.split(';'):
    if statement.strip():
        cursor.execute(statement)

conn.commit()
conn.close()

print("Database has been reset.")
