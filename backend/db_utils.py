# backend/db.py
import csv
import os
import sqlite3
import sys
import traceback

from flask import current_app, g
from werkzeug.security import generate_password_hash


def _ensure_dir_for_db(path: str) -> None:
    """
    Crea el directorio de la base de datos si aplica.
    Evita hacerlo para SQLite en memoria o paths vacíos.
    """
    if not path:
        return

    # Casos de SQLite en memoria o URL vacía
    in_memory_markers = {":memory:", "sqlite://", "sqlite:///:memory:"}
    # Normaliza minisculas para comparar prefijos sqlite
    if path in in_memory_markers:
        return

    # Si es una URL SQLAlchemy que apunta a archivo sqlite local, podría ser "sqlite:///ruta/archivo.db"
    if path.startswith("sqlite:///"):
        fs_path = path.replace("sqlite:///", "", 1)
        dir_ = os.path.dirname(os.path.abspath(fs_path))
    else:
        # Ruta de archivo plano
        dir_ = os.path.dirname(os.path.abspath(path))

    if dir_:
        os.makedirs(dir_, exist_ok=True)


def get_db():
    if "db" not in g:
        try:
            path = current_app.config["DATABASE"]
            # Ensure the directory for the database file exists
            _ensure_dir_for_db(path)
            g.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            # Log the error to console, as dbmod.log_error would call get_db() again
            print(f"ERROR: Could not connect to database in get_db: {e}")
            traceback.print_exc()
            g.db = None # Set g.db to None to avoid repeated attempts
            return None # Return None to indicate failure
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db_func():
    """Seeds the database with initial data if tables are empty."""
    print("--- [START] Database Seeding ---", flush=True)
    try:
        db = get_db()
        if db is None:
            print("[FATAL] get_db() returned None. Aborting.", file=sys.stderr, flush=True)
            return

        # Check if roles table is empty before seeding
        cursor = db.execute('SELECT COUNT(id) FROM roles')
        if cursor.fetchone()[0] == 0:
            print("[INFO] Seeding roles table from CSV.", flush=True)
            try:
                with open(os.path.join(current_app.root_path, 'data', 'roles.csv'), encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header row
                    roles = [tuple(row) for row in reader]
                db.executemany("INSERT INTO roles (code, descripcion) VALUES (?, ?)", roles)
                print("[INFO] Roles seeded successfully from CSV.", flush=True)
            except Exception as e:
                print(f"[ERROR] Failed to seed roles from CSV: {e}", file=sys.stderr, flush=True)
        else:
            print("[INFO] Roles table already seeded. Skipping.", flush=True)

        # Check if users table is empty before seeding
        cursor = db.execute('SELECT COUNT(id) FROM users')
        if cursor.fetchone()[0] == 0:
            print("[INFO] Seeding users table from CSV.", flush=True)
            try:
                with open(os.path.join(current_app.root_path, 'data', 'users.csv'), encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header row
                    users = []
                    for row in reader:
                        username, password, role, nombre, email = row
                        hashed_password = generate_password_hash(password)
                        users.append((username, hashed_password, role, nombre, email))
                db.executemany("INSERT INTO users (username, password_hash, role, nombre, email) VALUES (?, ?, ?, ?, ?)", users)
                print("[INFO] Users seeded successfully from CSV.", flush=True)

                # Seed user_roles right after seeding users
                print("[INFO] Seeding user_roles table.", flush=True)
                user_roles = []
                for user_role in ['admin', 'oficina', 'cliente', 'autonomo']:
                    cursor = db.execute("SELECT id FROM users WHERE username = ?", (user_role,))
                    user_row = cursor.fetchone()
                    cursor = db.execute("SELECT id FROM roles WHERE code = ?", (user_role,))
                    role_row = cursor.fetchone()
                    if user_row and role_row:
                        user_roles.append((user_row['id'], role_row['id']))
                if user_roles:
                    db.executemany("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", user_roles)
                    print("[INFO] user_roles seeded successfully.", flush=True)

            except Exception as e:
                print(f"[ERROR] Failed to seed users from CSV: {e}", file=sys.stderr, flush=True)
        else:
            print("[INFO] Users table already seeded. Skipping.", flush=True)

        db.commit()
        print("[INFO] Seeding process complete.", flush=True)

    except Exception as e:
        print(f"[FATAL] An error occurred during database seeding: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        if 'db' in locals() and db is not None:
            db.rollback()
            print("[INFO] Database changes rolled back.", flush=True)
    finally:
        print("--- [END] Database Seeding ---", flush=True)


def _execute_sql(sql, db_conn, params=(), cursor=None, fetchone=False, fetchall=False, commit=False):
    """
    A helper function to execute SQL queries.
    It can execute a script if no params are provided, or a single statement with params.
    """
    if cursor is None:
        if db_conn is None:
            current_app.logger.error("Database connection error in _execute_sql: db_conn is None.")
            return None
        cursor = db_conn.cursor()

    # Use executescript for multi-statement SQL scripts (like schema.sql) when no params are passed
    if not params:
        cursor.executescript(sql)
    # Use execute for single, parameterized queries
    else:
        cursor.execute(sql, params)

    if commit:
        db_conn.commit()

    if fetchone:
        return cursor.fetchone()

    if fetchall:
        return cursor.fetchall()

def init_app(app):
    app.teardown_appcontext(close_db)



def log_error(level, message, details=None):
    try:
        db = get_db()
        if db is None:
            print(f"Failed to get DB connection for logging error: {message}")
            return
        db.execute(
            "INSERT INTO error_log(level, message, details) VALUES (?,?,?)",
            (level, message, details),
        )
        db.commit()
    except Exception as e:
        # Avoid crashing if logging itself fails
        print(f"Failed to log error to DB: {e}")
