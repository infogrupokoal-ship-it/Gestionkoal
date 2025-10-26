import csv
import os
import sys
import traceback

from flask import current_app, g
from werkzeug.security import generate_password_hash
from sqlalchemy import text

from backend.extensions import db # Import the global db instance
from sqlalchemy import text as sql_text

class SessionProxy:
    def __init__(self, session):
        self._session = session

    def execute(self, statement, params=None):
        # Support raw SQLite-style SQL strings and SQLAlchemy text/ClauseElement
        if isinstance(statement, str):
            if '?' in statement:
                # Use DB-API execution for qmark paramstyle
                bind = self._session.get_bind()
                with bind.connect() as conn:
                    return conn.exec_driver_sql(statement, params)
            # Fallback to SQLAlchemy text()
            return self._session.execute(sql_text(statement), params or {})
        # Already a ClauseElement or TextClause
        return self._session.execute(statement, params or {})

    def __getattr__(self, name):
        return getattr(self._session, name)

def get_db():
    """
    Returns the SQLAlchemy session.
    This function is kept for backward compatibility but new code should use `db.session` directly.
    """
    return SessionProxy(db.session)

def init_db_func():
    """Seeds the database with initial data if tables are empty."""
    print("--- [START] Database Seeding ---", flush=True)
    try:
        # Check if roles table is empty before seeding
        roles_count = db.session.execute(text('SELECT COUNT(id) FROM roles')).scalar()
        if roles_count == 0:
            print("[INFO] Seeding roles table from CSV.", flush=True)
            try:
                # Assuming roles.csv is in current_app.root_path/data/
                with open(os.path.join(current_app.root_path, 'data', 'roles.csv'), encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header row
                    roles_data = []
                    for row in reader:
                        if len(row) == 2: # Ensure row has expected number of columns
                            roles_data.append({"code": row[0], "descripcion": row[1]})
                        else:
                            print(f"[WARNING] Skipping malformed row in roles.csv: {row}", file=sys.stderr, flush=True)
                if roles_data:
                    db.session.execute(text("INSERT INTO roles (code, descripcion) VALUES (:code, :descripcion)"), roles_data)
                print("[INFO] Roles seeded successfully from CSV.", flush=True)
            except Exception as e:
                print(f"[ERROR] Failed to seed roles from CSV: {e}", file=sys.stderr, flush=True)
        else:
            print("[INFO] Roles table already seeded. Skipping.", flush=True)

        # Check if users table is empty before seeding
        users_count = db.session.execute(text('SELECT COUNT(id) FROM users')).scalar()
        if users_count == 0:
            print("[INFO] Seeding users table from CSV.", flush=True)
            try:
                # Assuming users.csv is in current_app.root_path/data/
                with open(os.path.join(current_app.root_path, 'data', 'users.csv'), encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header row
                    users_data = []
                    for row in reader:
                        if len(row) == 5: # Ensure row has expected number of columns
                            username, password, role, nombre, email = row
                            hashed_password = generate_password_hash(password)
                            users_data.append({"username": username, "password_hash": hashed_password, "role": role, "nombre": nombre, "email": email})
                        else:
                            print(f"[WARNING] Skipping malformed row in users.csv: {row}", file=sys.stderr, flush=True)
                if users_data:
                    db.session.execute(text("INSERT INTO users (username, password_hash, role, nombre, email) VALUES (:username, :password_hash, :role, :nombre, :email)"), users_data)
                print("[INFO] Users seeded successfully from CSV.", flush=True)

                # Seed user_roles right after seeding users
                print("[INFO] Seeding user_roles table.", flush=True)
                user_roles_data = []
                for user_role_code in ['admin', 'oficina', 'cliente', 'autonomo']:
                    user_row = db.session.execute(text("SELECT id FROM users WHERE username = :username"), {"username": user_role_code}).fetchone()
                    role_row = db.session.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": user_role_code}).fetchone()
                    if user_row and role_row:
                        user_roles_data.append({"user_id": user_row.id, "role_id": role_row.id})
                if user_roles_data:
                    db.session.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"), user_roles_data)
                    print("[INFO] user_roles seeded successfully.", flush=True)

            except Exception as e:
                print(f"[ERROR] Failed to seed users from CSV: {e}", file=sys.stderr, flush=True)
        else:
            print("[INFO] Users table already seeded. Skipping.", flush=True)

        db.session.commit()
        print("[INFO] Seeding process complete.", flush=True)

    except Exception as e:
        print(f"[FATAL] An error occurred during database seeding: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        db.session.rollback()
        print("[INFO] Database changes rolled back.", flush=True)
    finally:
        print("--- [END] Database Seeding ---", flush=True)

def init_app(app):
    # Flask-SQLAlchemy handles session teardown automatically
    pass

def log_error(level, message, details=None):
    try:
        db.session.execute(
            text("INSERT INTO error_log(level, message, details) VALUES (:level, :message, :details)"),
            {"level": level, "message": message, "details": details},
        )
        db.session.commit()
    except Exception as e:
        # Avoid crashing if logging itself fails
        print(f"Failed to log error to DB: {e}")
