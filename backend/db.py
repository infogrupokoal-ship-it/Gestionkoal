# backend/db.py
import csv
import os
import sqlite3
import sys
import traceback
from pathlib import Path
from sqlite3 import Connection as SQLite3Connection

import click
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
                        username, password, role, nombre, email, whatsapp_verified, referral_code, referred_by_user_id = row
                        hashed_password = generate_password_hash(password)
                        users.append((username, hashed_password, role, nombre, email, whatsapp_verified, referral_code, referred_by_user_id))
                db.executemany("INSERT INTO users (username, password_hash, role, nombre, email, whatsapp_verified, referral_code, referred_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", users)
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


def _execute_sql(sql, params=(), cursor=None, fetchone=False, fetchall=False, commit=False):
    """
    A helper function to execute SQL queries.
    """
    if cursor is None:
        db = get_db()
        if db is None:
            current_app.logger.error("Database connection error in _execute_sql.")
            return None # Or raise an exception, depending on desired error handling
        cursor = db.cursor()

    cursor.execute(sql, params)

    if commit:
        db = get_db()
        db.commit()

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

def apply_schema_sql_on_connection(conn, sql_path="schema.sql"):
    """
    Aplica el schema.sql sobre una conexión SQLite/SQLAlchemy *ya abierta*,
    garantizando que la automap/reflection verá las tablas.
    """
    sql = Path(sql_path).read_text(encoding="utf-8")
    raw_conn = conn
    # si es conexión SQLAlchemy, obtener DBAPI connection
    if hasattr(conn, "connection"):
        raw_conn = conn.connection
    if isinstance(raw_conn, SQLite3Connection):
        raw_conn.executescript(sql)  # ejecuta todo el script de una vez
    else:
        # fallback para otros motores
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            conn.execute(stmt)

def _get_engine():
    try:
        from backend.extensions import db as _sqla
        return getattr(_sqla, "engine", None)
    except Exception:
        return None

class _LazyEngine:
    def raw_connection(self, *args, **kwargs):
        eng = _get_engine()
        if eng is None:
            raise RuntimeError("SQLAlchemy engine is not initialized")
        return eng.raw_connection(*args, **kwargs)
    def connect(self, *args, **kwargs):
        eng = _get_engine()
        if eng is None:
            raise RuntimeError("SQLAlchemy engine is not initialized")
        return eng.connect(*args, **kwargs)

engine = _LazyEngine()

def get_engine():
    return _get_engine()
