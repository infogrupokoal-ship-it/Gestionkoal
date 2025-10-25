import sqlite3, os

DB_PATH = os.path.join('instance', 'gestion_avisos.sqlite')
ADMIN_USERNAME = 'admin'
NEW_PHONE_E164 = '34633660438'  # +34 633... en E.164 sin +

def run():
    if not os.path.exists(DB_PATH):
        print(f"BD no encontrada: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Asegúrate de los nombres de columnas correctos según tu esquema:
    # users(username, whatsapp_number, whatsapp_verified)
    cur.execute("SELECT id, username, whatsapp_number, whatsapp_verified FROM users WHERE username = ?", (ADMIN_USERNAME,))
    row = cur.fetchone()
    if not row:
        print("No existe usuario 'admin'.")
        conn.close()
        return

    cur.execute("""
        UPDATE users
           SET whatsapp_number = ?,
               whatsapp_verified = 1
         WHERE username = ?
    """, (NEW_PHONE_E164, ADMIN_USERNAME))
    conn.commit()
    print(f"✔ Admin actualizado con teléfono {NEW_PHONE_E164} y verificado=1.")
    conn.close()

if __name__ == "__main__":
    run()
