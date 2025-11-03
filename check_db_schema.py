import sqlite3

db_path = 'C:\\proyecto\\gestion_avisos\\instance\\gestion_avisos.sqlite'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(materiales)")
    columns = cursor.fetchall()

    print("Schema for 'materiales' table:")
    for col in columns:
        print(col)

except sqlite3.Error as e:
    print(f"Database error: {e}")
finally:
    if conn:
        conn.close()
