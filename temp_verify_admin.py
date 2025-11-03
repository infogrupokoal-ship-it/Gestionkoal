import sqlite3
import os

DATABASE = os.path.join('instance', 'gestion_avisos.sqlite')

def verify_admin_user():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT id, username, password_hash, email, nombre, nif, avatar_url FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()

        if admin_user:
            print(f"Usuario admin encontrado:")
            print(f"  ID: {admin_user[0]}")
            print(f"  Username: {admin_user[1]}")
            print(f"  Password Hash: {admin_user[2]}")
            print(f"  Email: {admin_user[3]}")
            print(f"  Nombre: {admin_user[4]}")
            print(f"  NIF: {admin_user[5]}")
            print(f"  Avatar URL: {admin_user[6]}")
        else:
            print("Usuario admin NO encontrado en la base de datos.")
    except sqlite3.Error as e:
        print(f"Error de SQLite: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    verify_admin_user()
