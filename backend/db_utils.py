import csv
import os
import sqlite3  # Added
import sys
import traceback

from flask import current_app
from sqlalchemy import text
from sqlalchemy import text as sql_text
from werkzeug.security import generate_password_hash

from backend.extensions import db  # Import the global db instance


class SessionProxy:
    def __init__(self, session):
        self._session = session

    def execute(self, statement, params=None):
        # Support raw SQLite-style SQL strings and SQLAlchemy text/ClauseElement
        if isinstance(statement, str):
            if "?" in statement:
                # Use DB-API execution for qmark paramstyle, return mappings for dict-like rows
                bind = self._session.get_bind()
                with bind.connect() as conn:
                    return conn.exec_driver_sql(statement, params).mappings()
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
    """
    Seeds the database with initial data if tables are empty.
    """
    print("--- [START] Database Seeding ---", flush=True)
    try:
        # Check if roles table is empty before seeding
        roles_count = db.session.execute(text("SELECT COUNT(id) FROM roles")).scalar()
        if roles_count == 0:
            print("[INFO] Seeding roles table from CSV.", flush=True)
            try:
                # Assuming roles.csv is in current_app.root_path/data/
                with open(
                    os.path.join(current_app.root_path, "data", "roles.csv"),
                    encoding="utf-8",
                ) as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header row
                    roles_data = []
                    for row in reader:
                        if len(row) == 2:  # Ensure row has expected number of columns
                            roles_data.append({"code": row[0], "descripcion": row[1]})
                        else:
                            print(
                                f"[WARNING] Skipping malformed row in roles.csv: {row}",
                                file=sys.stderr,
                                flush=True,
                            )
                if roles_data:
                    db.session.execute(
                        text(
                            "INSERT INTO roles (code, descripcion) VALUES (:code, :descripcion)"
                        ),
                        roles_data,
                    )
                print("[INFO] Roles seeded successfully from CSV.", flush=True)
            except Exception as e:
                print(
                    f"[ERROR] Failed to seed roles from CSV: {e}",
                    file=sys.stderr,
                    flush=True,
                )
        else:
            print("[INFO] Roles table already seeded. Skipping.", flush=True)

        # Check if users table is empty before seeding
        users_count = db.session.execute(text("SELECT COUNT(id) FROM users")).scalar()
        if users_count == 0:
            print("[INFO] Seeding users table from CSV.", flush=True)
            try:
                # Assuming users.csv is in current_app.root_path/data/
                with open(
                    os.path.join(current_app.root_path, "data", "users.csv"),
                    encoding="utf-8",
                ) as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header row
                    users_data = []
                    for row in reader:
                        if len(row) == 5:  # Ensure row has expected number of columns
                            username, password, role, nombre, email = row
                            hashed_password = generate_password_hash(password)
                            users_data.append(
                                {
                                    "username": username,
                                    "password_hash": hashed_password,
                                    "role": role,
                                    "nombre": nombre,
                                    "email": email,
                                }
                            )
                        else:
                            print(
                                f"[WARNING] Skipping malformed row in users.csv: {row}",
                                file=sys.stderr,
                                flush=True,
                            )
                if users_data:
                    db.session.execute(
                        text(
                            "INSERT INTO users (username, password_hash, role, nombre, email) VALUES (:username, :password_hash, :role, :nombre, :email)"
                        ),
                        users_data,
                    )
                print("[INFO] Users seeded successfully from CSV.", flush=True)

                # Seed user_roles right after seeding users
                print("[INFO] Seeding user_roles table.", flush=True)
                user_roles_data = []
                for user_role_code in ["admin", "oficina", "cliente", "autonomo"]:
                    user_row = db.session.execute(
                        text("SELECT id FROM users WHERE username = :username"),
                        {"username": user_role_code},
                    ).fetchone()
                    role_row = db.session.execute(
                        text("SELECT id FROM roles WHERE code = :code"),
                        {"code": user_role_code},
                    ).fetchone()
                    if user_row and role_row:
                        user_roles_data.append(
                            {"user_id": user_row.id, "role_id": role_row.id}
                        )
                if user_roles_data:
                    db.session.execute(
                        text(
                            "INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"
                        ),
                        user_roles_data,
                    )
                    print("[INFO] user_roles seeded successfully.", flush=True)

            except Exception as e:
                print(
                    f"[ERROR] Failed to seed users from CSV: {e}",
                    file=sys.stderr,
                    flush=True,
                )
        else:
            print("[INFO] Users table already seeded. Skipping.", flush=True)

        db.session.commit()
        print("[INFO] Seeding process complete.", flush=True)

    except Exception as e:
        print(
            f"[FATAL] An error occurred during database seeding: {e}",
            file=sys.stderr,
            flush=True,
        )
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
            text(
                "INSERT INTO error_log(level, message, details) VALUES (:level, :message, :details)"
            ),
            {"level": level, "message": message, "details": details},
        )
        db.session.commit()
    except Exception as e:
        # Avoid crashing if logging itself fails
        print(f"Failed to log error to DB: {e}")

def insertar_material(material):
    try:
        db.session.execute(text("""
            INSERT OR IGNORE INTO materiales
            (nombre, descripcion, categoria, precio_costo_estimado, precio_venta_sugerido,
             unidad_medida, proveedor_sugerido, stock_minimo, tiempo_entrega_dias, observaciones)
            VALUES (:nombre, :descripcion, :categoria, :precio_costo_estimado, :precio_venta_sugerido,
                    :unidad_medida, :proveedor_sugerido, :stock_minimo, :tiempo_entrega_dias, :observaciones)
        """), material)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def get_db_connection():
    conn = sqlite3.connect(current_app.config["DATABASE"])
    conn.row_factory = sqlite3.Row  # This enables column access by name: row["column_name"]
    return conn

def obtener_materiales():
    conn = get_db_connection()
    materiales = conn.execute("SELECT * FROM materiales").fetchall()
    conn.close()
    return [dict(m) for m in materiales]

def obtener_servicios():
    conn = get_db_connection()
    servicios = conn.execute("SELECT * FROM servicios").fetchall()
    conn.close()
    return [dict(s) for s in servicios]

def get_distinct_material_categories():
    conn = get_db_connection()
    categories = conn.execute("SELECT DISTINCT categoria FROM materiales WHERE categoria IS NOT NULL").fetchall()
    conn.close()
    return [c["categoria"] for c in categories]

def get_distinct_material_providers():
    conn = get_db_connection()
    providers = conn.execute("SELECT DISTINCT proveedor_sugerido FROM materiales WHERE proveedor_sugerido IS NOT NULL").fetchall()
    conn.close()
    return [p["proveedor_sugerido"] for p in providers]

def get_distinct_service_categories():
    conn = get_db_connection()
    categories = conn.execute("SELECT DISTINCT categoria FROM servicios WHERE categoria IS NOT NULL").fetchall()
    conn.close()
    return [c["categoria"] for c in categories]

def get_distinct_service_skills():
    conn = get_db_connection()
    skills = conn.execute("SELECT DISTINCT habilidades_requeridas FROM servicios WHERE habilidades_requeridas IS NOT NULL").fetchall()
    conn.close()
    return [s["habilidades_requeridas"] for s in skills]

def get_user_by_id(user_id):
    user = db.session.execute(text("SELECT * FROM users WHERE id = :user_id"), {"user_id": user_id}).fetchone()
    return dict(user) if user else None

def get_all_users():
    users = db.session.execute(text("SELECT * FROM users")).fetchall()
    return [dict(u) for u in users]

def get_all_roles():
    roles = db.session.execute(text("SELECT * FROM roles")).fetchall()
    return [dict(r) for r in roles]

def get_user_roles_by_id(user_id):
    roles = db.session.execute(text("SELECT role_id FROM user_roles WHERE user_id = :user_id"), {"user_id": user_id}).fetchall()
    return [r["role_id"] for r in roles]

def get_role_by_id(role_id):
    role = db.session.execute(text("SELECT * FROM roles WHERE id = :role_id"), {"role_id": role_id}).fetchone()
    return dict(role) if role else None

def get_role_by_code(role_code):
    role = db.session.execute(text("SELECT * FROM roles WHERE code = :role_code"), {"role_code": role_code}).fetchone()
    return dict(role) if role else None

def update_user_roles(user_id, new_role_ids):
    try:
        db.session.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), {"user_id": user_id})
        for role_id in new_role_ids:
            db.session.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"), {"user_id": user_id, "role_id": role_id})
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def get_total_jobs_by_category(days=30):
    query = text("""
        SELECT tipo, COUNT(id) as count
        FROM tickets
        WHERE fecha_creacion >= strftime('%Y-%m-%d %H:%M:%S', date('now', '-:days day'))
        GROUP BY tipo
        ORDER BY count DESC
    """)
    result = db.session.execute(query, {"days": days}).fetchall()
    return [dict(row) for row in result]

def get_most_used_services(limit=5):
    query = text("""
        SELECT s.nombre, COUNT(js.service_id) as usage_count
        FROM job_services js
        JOIN servicios s ON js.service_id = s.id
        GROUP BY s.nombre
        ORDER BY usage_count DESC
        LIMIT :limit
    """)
    result = db.session.execute(query, {"limit": limit}).fetchall()
    return [dict(row) for row in result]

def get_low_stock_materials():
    query = text("""
        SELECT nombre, stock, stock_minimo
        FROM materiales
        WHERE stock <= stock_minimo
        ORDER BY nombre
    """)
    result = db.session.execute(query).fetchall()
    return [dict(row) for row in result]

def get_estimated_service_hours(period='month'):
    # This is a simplified example. In a real app, you'd sum up time_estimado_horas from job_services
    # and potentially filter by date for actual jobs.
    # For now, let's just return a mock or aggregate from existing services.
    if period == 'month':
        return {"total_estimated_hours": 160, "period": "month"} # Mock data
    return {"total_estimated_hours": 40, "period": "week"} # Mock data

def get_top_clients(limit=5):
    query = text("""
        SELECT c.nombre, COUNT(t.id) as total_jobs
        FROM clientes c
        JOIN tickets t ON c.id = t.cliente_id
        GROUP BY c.nombre
        ORDER BY total_jobs DESC
        LIMIT :limit
    """)
    result = db.session.execute(query, {"limit": limit}).fetchall()
    return [dict(row) for row in result]
def insertar_servicio(servicio):
    try:
        db.session.execute(text("""
            INSERT OR IGNORE INTO servicios
            (nombre, descripcion, categoria, precio_base_estimado, unidad_medida,
             tiempo_estimado_horas, habilidades_requeridas, observaciones)
            VALUES (:nombre, :descripcion, :categoria, :precio_base_estimado, :unidad_medida,
                    :tiempo_estimado_horas, :habilidades_requeridas, :observaciones)
        """), servicio)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
