import os
import sqlite3

# Database path configuration
instance_path = os.path.join(os.getcwd(), 'instance')
os.makedirs(instance_path, exist_ok=True)
db_path = os.path.join(instance_path, 'gestion_avisos.sqlite')

print(f"Database path: {db_path}")

# Connect to the database (it will be created if it doesn't exist)
try:
    # Delete the DB file first to ensure a clean start
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database file.")

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Read and execute create_notifications_table.sql first
    notifications_schema_path = os.path.join(os.getcwd(), 'create_notifications_table.sql')
    if os.path.exists(notifications_schema_path):
        print(f"Reading notifications schema from {notifications_schema_path}")
        with open(notifications_schema_path, encoding='utf-8') as f:
            cur.executescript(f.read())
        print("Executed create_notifications_table.sql")

    # Read and execute the main schema.sql
    schema_path = os.path.join(os.getcwd(), 'schema.sql')
    if os.path.exists(schema_path):
        print(f"Reading main schema from {schema_path}")
        with open(schema_path, encoding='utf-8') as f:
            cur.executescript(f.read())
        print("Executed main schema.sql")

        # List all tables to verify
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        print(f"Tables created: {[t[0] for t in tables]}")
    else:
        print(f"ERROR: {schema_path} not found.")

    con.commit()
    con.close()

    print("Database initialized successfully from schema.sql.")

except Exception as e:
    print(f"An error occurred: {e}")