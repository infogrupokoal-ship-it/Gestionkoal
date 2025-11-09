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

        # Check if permissions table is empty before seeding
        permissions_count = db.session.execute(text("SELECT COUNT(id) FROM permissions")).scalar()
        if permissions_count == 0:
            print("[INFO] Seeding permissions table.", flush=True)
            permissions_data = [
                # Existing permissions
                {"code": "view_dashboard", "descripcion": "Ver el panel de control"},
                {"code": "manage_users", "descripcion": "Gestionar usuarios"},
                {"code": "view_jobs", "descripcion": "Ver trabajos"},
                {"code": "create_jobs", "descripcion": "Crear trabajos"},
                {"code": "edit_jobs", "descripcion": "Editar trabajos"},
                {"code": "delete_jobs", "descripcion": "Eliminar trabajos"},
                {"code": "view_clients", "descripcion": "Ver clientes"},
                {"code": "create_clients", "descripcion": "Crear clientes"},
                {"code": "edit_clients", "descripcion": "Editar clientes"},
                {"code": "delete_clients", "descripcion": "Eliminar clientes"},
                {"code": "view_services", "descripcion": "Ver servicios"},
                {"code": "create_services", "descripcion": "Crear servicios"},
                {"code": "edit_services", "descripcion": "Editar servicios"},
                {"code": "delete_services", "descripcion": "Eliminar servicios"},
                {"code": "view_materials", "descripcion": "Ver materiales"},
                {"code": "create_materials", "descripcion": "Crear materiales"},
                {"code": "edit_materials", "descripcion": "Editar materiales"},
                {"code": "delete_materials", "descripcion": "Eliminar materiales"},
                {"code": "view_providers", "descripcion": "Ver proveedores"},
                {"code": "create_providers", "descripcion": "Crear proveedores"},
                {"code": "edit_providers", "descripcion": "Editar proveedores"},
                {"code": "delete_providers", "descripcion": "Eliminar proveedores"},
                {"code": "view_freelancers", "descripcion": "Ver autónomos"},
                {"code": "create_freelancers", "descripcion": "Crear autónomos"},
                {"code": "edit_freelancers", "descripcion": "Editar autónomos"},
                {"code": "delete_freelancers", "descripcion": "Eliminar autónomos"},
                {"code": "view_own_commissions", "descripcion": "Ver mis comisiones"},
                {"code": "view_price_requests", "descripcion": "Ver solicitudes de precio"},
                {"code": "create_price_requests", "descripcion": "Crear solicitudes de precio"},
                {"code": "manage_price_requests", "descripcion": "Gestionar solicitudes de precio"},
                {"code": "view_invoices", "descripcion": "Ver facturas"},
                {"code": "create_invoices", "descripcion": "Crear facturas"},
                {"code": "manage_invoices", "descripcion": "Gestionar facturas"},
                {"code": "view_time_sheets", "descripcion": "Ver partes de horas"},
                {"code": "add_time_sheets", "descripcion": "Añadir partes de horas"},
                {"code": "edit_time_sheets", "descripcion": "Editar partes de horas"},
                {"code": "delete_time_sheets", "descripcion": "Eliminar partes de horas"},
                # New permissions for liquidations
                {"code": "view_liquidations", "descripcion": "Ver liquidaciones"},
                {"code": "generate_liquidations", "descripcion": "Generar liquidaciones"},
                {"code": "manage_liquidations", "descripcion": "Gestionar liquidaciones"},
            ]
            db.session.execute(
                text("INSERT INTO permissions (code, descripcion) VALUES (:code, :descripcion)"),
                permissions_data,
            )
            print("[INFO] Permissions seeded successfully.", flush=True)
        else:
            print("[INFO] Permissions table already seeded. Skipping.", flush=True)

        # Seed role_permissions if empty
        role_permissions_count = db.session.execute(text("SELECT COUNT(id) FROM role_permissions")).scalar()
        if role_permissions_count == 0:
            print("[INFO] Seeding role_permissions table.", flush=True)
            admin_role_id = db.session.execute(text("SELECT id FROM roles WHERE code = 'admin'")).scalar()
            oficina_role_id = db.session.execute(text("SELECT id FROM roles WHERE code = 'oficina'")).scalar()
            comercial_role_id = db.session.execute(text("SELECT id FROM roles WHERE code = 'comercial'")).scalar()
            autonomo_role_id = db.session.execute(text("SELECT id FROM roles WHERE code = 'autonomo'")).scalar()
            cliente_role_id = db.session.execute(text("SELECT id FROM roles WHERE code = 'cliente'")).scalar()

            all_permissions = db.session.execute(text("SELECT id, code FROM permissions")).fetchall()
            
            role_permissions_data = []

            for perm_id, perm_code in all_permissions:
                if admin_role_id:
                    role_permissions_data.append({"role_id": admin_role_id, "permission_id": perm_id})
                
                if oficina_role_id:
                    if perm_code in [
                        "view_dashboard", "view_jobs", "create_jobs", "edit_jobs", "delete_jobs",
                        "view_clients", "create_clients", "edit_clients", "delete_clients",
                        "view_services", "create_services", "edit_services", "delete_services",
                        "view_materials", "create_materials", "edit_materials", "delete_materials",
                        "view_providers", "create_providers", "edit_providers", "delete_providers",
                        "view_freelancers", "create_freelancers", "edit_freelancers", "delete_freelancers",
                        "view_price_requests", "create_price_requests", "manage_price_requests",
                        "view_invoices", "create_invoices", "manage_invoices",
                        "view_time_sheets", "add_time_sheets", "edit_time_sheets", "delete_time_sheets",
                        "view_liquidations", "generate_liquidations", "manage_liquidations", # New liquidations permissions
                    ]:
                        role_permissions_data.append({"role_id": oficina_role_id, "permission_id": perm_id})
                
                if comercial_role_id:
                    if perm_code in [
                        "view_dashboard", "view_jobs", "create_jobs", "edit_jobs",
                        "view_clients", "create_clients", "edit_clients",
                        "view_own_commissions", "view_price_requests", "create_price_requests",
                    ]:
                        role_permissions_data.append({"role_id": comercial_role_id, "permission_id": perm_id})
                
                if autonomo_role_id:
                    if perm_code in [
                        "view_dashboard", "view_jobs", "edit_jobs", # Autonomos can view and update their assigned jobs
                        "view_materials", "view_services",
                        "view_time_sheets", "add_time_sheets", "edit_time_sheets", # Autonomos manage their own time sheets
                        "view_liquidations", # Autonomos can view their own liquidations
                    ]:
                        role_permissions_data.append({"role_id": autonomo_role_id, "permission_id": perm_id})
                
                if cliente_role_id:
                    if perm_code in [
                        "view_jobs", # Clientes can view their own jobs
                        "view_invoices", # Clientes can view their own invoices
                    ]:
                        role_permissions_data.append({"role_id": cliente_role_id, "permission_id": perm_id})

            if role_permissions_data:
                db.session.execute(
                    text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"),
                    role_permissions_data,
                )
                print("[INFO] role_permissions seeded successfully.", flush=True)
        else:
            print("[INFO] role_permissions table already seeded. Skipping.", flush=True)

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
