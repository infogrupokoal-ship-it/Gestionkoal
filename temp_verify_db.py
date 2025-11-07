import os
import sqlite3

db_path = os.path.join(os.getcwd(), 'instance', 'gestion_avisos.sqlite')

if not os.path.exists(db_path):
    print(f"ERROR: Database file not found at {db_path}")
    exit()

queries = {
    "Cliente Nuevo": "SELECT id, telefono, nombre FROM clientes ORDER BY id DESC LIMIT 1",
    "Ticket Nuevo": "SELECT id, cliente_id, titulo, prioridad, estado, asignado_a FROM tickets ORDER BY id DESC LIMIT 1",
    "Logs de IA": "SELECT id, event_type, ticket_id, output FROM ai_logs ORDER BY id DESC LIMIT 2",
    "Logs de WhatsApp": "SELECT direction, phone, status, message FROM whatsapp_logs ORDER BY id DESC LIMIT 2"
}

try:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    for title, query in queries.items():
        print(f"\n--- {title} ---")
        try:
            cur.execute(query)
            rows = cur.fetchall()
            if not rows:
                print("No results found.")
            else:
                for row in rows:
                    print(dict(row))
        except sqlite3.Error as e:
            print(f"Error executing query: {e}")

    con.close()

except Exception as e:
    print(f"An error occurred: {e}")

