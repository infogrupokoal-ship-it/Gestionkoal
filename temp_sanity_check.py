import os
import sqlite3

# Get the absolute path to the database file
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'gestion_avisos.sqlite')

def check_table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def get_table_columns(conn, table_name):
    """Get the column names of a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def main():
    """Main function to perform the sanity check."""
    try:
        conn = sqlite3.connect(db_path)
        print("Successfully connected to the database.")

        # Check for 'users' table
        if not check_table_exists(conn, 'users'):
            print("ERROR: 'users' table does not exist.")
            return

        # Check for 'freelancers' table
        if not check_table_exists(conn, 'freelancers'):
            print("ERROR: 'freelancers' table does not exist.")
            return

        # Check for columns in 'users' table
        users_columns = get_table_columns(conn, 'users')
        expected_users_columns = [
            'id', 'username', 'password_hash', 'email', 'nombre', 'apellidos',
            'telefono', 'direccion', 'ciudad', 'provincia', 'cp', 'nif',
            'fecha_alta', 'last_login', 'is_active', 'is_admin', 'role',
            'whatsapp_number', 'whatsapp_opt_in', 'costo_por_hora',
            'tasa_recargo', 'whatsapp_verified', 'whatsapp_code',
            'whatsapp_code_expires'
        ]
        missing_users_columns = set(expected_users_columns) - set(users_columns)
        if missing_users_columns:
            print(f"ERROR: Missing columns in 'users' table: {', '.join(missing_users_columns)}")
            return

        # Check for columns in 'freelancers' table
        freelancers_columns = get_table_columns(conn, 'freelancers')
        expected_freelancers_columns = [
            'id', 'user_id', 'category', 'specialty', 'city_province', 'web',
            'notes', 'source_url', 'hourly_rate_normal', 'hourly_rate_tier2',
            'hourly_rate_tier3', 'difficulty_surcharge_rate', 'recargo_zona',
            'recargo_dificultad'
        ]
        missing_freelancers_columns = set(expected_freelancers_columns) - set(freelancers_columns)
        if missing_freelancers_columns:
            print(f"ERROR: Missing columns in 'freelancers' table: {', '.join(missing_freelancers_columns)}")
            return

        print("Sanity check passed successfully. The database schema seems to be in sync with the application.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
