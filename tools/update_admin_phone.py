import sqlite3
import os

# --- Configuración ---
DB_PATH = os.path.join('instance', 'gestion_avisos.sqlite')
ADMIN_USERNAME = 'admin' 
NEW_PHONE_NUMBER = '34633660438'  # Tu número en formato internacional E.164
# -------------------

def update_phone():
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encontró la base de datos en {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Verificar si el usuario existe
        cursor.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,))
        user = cursor.fetchone()

        if user is None:
            print(f"Error: No se encontró al usuario '{ADMIN_USERNAME}'.")
            return

        # Actualizar el número de teléfono
        cursor.execute("UPDATE users SET whatsapp_number = ? WHERE username = ?", (NEW_PHONE_NUMBER, ADMIN_USERNAME))
        conn.commit()

        if cursor.rowcount > 0:
            print(f"¡Éxito! El número de WhatsApp para el usuario '{ADMIN_USERNAME}' se ha actualizado a '{NEW_PHONE_NUMBER}'.")
            print("Ahora puedes probar el reenvío del código de confirmación.")
        else:
            print("No se actualizó ninguna fila. ¿Estás seguro de que el nombre de usuario es correcto?")

    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    update_phone()
