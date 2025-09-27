import sqlite3
import os

DATABASE = os.environ.get('DATABASE_PATH', os.path.join(os.getcwd(), 'instance', 'gestion_avisos.sqlite'))

def seed_roles():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    roles = [
        ('admin', 'Administrador del sistema'),
        ('oficina', 'Personal de oficina'),
        ('jefe_obra', 'Jefe de obra'),
        ('tecnico', 'Técnico de campo'),
        ('autonomo', 'Trabajador autónomo'),
        ('cliente', 'Cliente final'),
        ('proveedor', 'Proveedor de servicios/materiales')
    ]

    try:
        for code, descripcion in roles:
            cursor.execute("INSERT OR IGNORE INTO roles (code, descripcion) VALUES (?, ?)", (code, descripcion))
        conn.commit()
        print("Roles seeded successfully.")
    except sqlite3.IntegrityError:
        print("Roles already exist, skipping insertion.")
    except Exception as e:
        print(f"Error seeding roles: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    # Ensure the instance directory exists for the database
    instance_path = os.path.join(os.getcwd(), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    seed_roles()
