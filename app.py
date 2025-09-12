# import psycopg2
# import psycopg2.extras
import sqlite3
import click
import csv  # New import
import os  # New import
import re  # New import
import urllib.parse  # New import
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
    send_from_directory,
)  # Added current_app
from datetime import datetime, timedelta  # Added timedelta for snooze
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # New import
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from functools import wraps  # New import for decorator


# Custom permission decorator
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Necesitas iniciar sesión para acceder a esta página.", "warning")
                return redirect(url_for("login"))
            if not current_user.has_permission(permission_name):
                flash(
                    f"No tienes permiso para realizar esta acción: {permission_name}.",
                    "danger",
                )
                return redirect(url_for("dashboard"))  # Redirect to a safe page
            return f(*args, **kwargs)

        return decorated_function

    return decorator


app = Flask(__name__)
app.secret_key = "grupokoal_super_secret_key" # Forced update to trigger Render deploy
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

def _execute_sql(cursor, sql, params=None, is_sqlite=False):
    if params is None:
        params = []
    if is_sqlite:
        cursor.execute(sql, params)
    else:
        # For psycopg2, use %s placeholders
        formatted_sql = sql.replace('?', '%s')
        cursor.execute(formatted_sql, params)


def setup_new_database(conn, is_sqlite=False):
    """Sets up a new database with schema and essential data like roles and permissions."""
    cursor = conn.cursor()
    print("--- Starting setup_new_database ---")

    # 1. Create schema
    print("--- Creating schema ---")
    with current_app.open_resource("schema.sql", mode="r") as f:
        schema_sql = f.read()
        if is_sqlite:
            # Adjust schema for SQLite if needed
            schema_sql = schema_sql.replace(
                "SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT"
            )
            schema_sql = schema_sql.replace(
                "TEXT UNIQUE NOT NULL", "TEXT UNIQUE NOT NULL COLLATE NOCASE"
            )
            schema_sql = schema_sql.replace("TEXT", "TEXT COLLATE NOCASE")
            schema_sql = schema_sql.replace(
                "TIMESTAMP DEFAULT NOW()", "DATETIME DEFAULT CURRENT_TIMESTAMP"
            )
            schema_sql = schema_sql.replace("DOUBLE PRECISION", "REAL")
            schema_sql = schema_sql.replace("NUMERIC", "REAL")
            schema_sql = schema_sql.replace("JSONB", "TEXT")
        else:  # Adjust schema for PostgreSQL if needed
            # Handle BOOLEAN defaults using regex for robustness
            schema_sql = re.sub(
                r"BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE", schema_sql
            )
            schema_sql = re.sub(
                r"BOOLEAN DEFAULT 1", "BOOLEAN DEFAULT TRUE", schema_sql
            )

            schema_sql = schema_sql.replace(
                "INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"
            )
            schema_sql = schema_sql.replace("REAL", "NUMERIC")
            # More specific TEXT replacements first
            schema_sql = schema_sql.replace(
                "TEXT UNIQUE NOT NULL", "VARCHAR UNIQUE NOT NULL"
            )
            schema_sql = schema_sql.replace("TEXT UNIQUE", "VARCHAR UNIQUE")
            schema_sql = schema_sql.replace("TEXT NOT NULL", "VARCHAR NOT NULL")
            schema_sql = schema_sql.replace(
                "TEXT", "VARCHAR"
            )  # General TEXT to VARCHAR

        if is_sqlite:
            cursor.executescript(schema_sql)
        else:
            # For PostgreSQL, execute line by line to handle potential errors better
            # and to allow for comments and multiple statements per line
            for statement in schema_sql.split(";"):
                if statement.strip():
                    try:
                        cursor.execute(statement + ";")
                    except Exception as e:
                        print(f"Error executing statement: {statement.strip()} - {e}")
                        conn.rollback()
                        raise  # Re-raise the exception after logging
            conn.commit()  # Commit after schema creation for PostgreSQL
    print("--- Schema created ---")

    # 2. Insert roles
    print("--- Inserting roles ---")
    roles_to_add = ["Admin", "Oficinista", "Autonomo", "Cliente", "Proveedor"]  # Added Cliente and Proveedor roles
    for role_name in roles_to_add:
        if is_sqlite:
            cursor.execute(
                "INSERT OR IGNORE INTO roles (name) VALUES (?)", (role_name,)
            )
        else:
            cursor.execute(
                "INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (role_name,),
            )
    conn.commit()

    # Fetch role IDs
    if is_sqlite:
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Admin',), is_sqlite=is_sqlite)
        admin_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Oficinista',), is_sqlite=is_sqlite)
        oficinista_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Autonomo',), is_sqlite=is_sqlite)
        autonomo_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Cliente',), is_sqlite=is_sqlite)
        cliente_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Proveedor',), is_sqlite=is_sqlite)
        proveedor_role_id = cursor.fetchone()["id"]
    else:
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Admin',), is_sqlite=is_sqlite)
        admin_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Oficinista',), is_sqlite=is_sqlite)
        oficinista_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Autonomo',), is_sqlite=is_sqlite)
        autonomo_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Cliente',), is_sqlite=is_sqlite)
        cliente_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Proveedor',), is_sqlite=is_sqlite)
        proveedor_role_id = cursor.fetchone()[0]

    print("--- Inserting permissions ---")
    # 3. Insert permissions
    permissions_to_add = [
        "view_users",
        "manage_users",
        "view_clients",
        "manage_clients",
        "view_services",
        "manage_services",
        "view_freelancers",
        "view_materials",
        "manage_materials",
        "view_proveedores",
        "manage_proveedores",
        "view_financial_reports",
        "manage_csv_import",
        "view_all_jobs",
        "manage_all_jobs",
        "view_own_jobs",
        "manage_own_jobs",
        "view_all_tasks",
        "manage_all_tasks",
        "view_own_tasks",
        "manage_own_tasks",
        "manage_notifications",
        "create_quotes",
        "upload_files",
        "create_new_job",  # New permission for adding jobs
    ]
    for perm_name in permissions_to_add:
        if is_sqlite:
            cursor.execute(
                "INSERT OR IGNORE INTO permissions (name) VALUES (?)", (perm_name,)
            )
        else:
            cursor.execute(
                "INSERT INTO permissions (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (perm_name,),
            )
    conn.commit()
    print("--- Permissions inserted ---")

    # 4. Assign permissions to roles
    print("--- Assigning permissions to roles ---")

    def assign_permission(role_id, perm_name):
        if is_sqlite:
            cursor.execute("SELECT id FROM permissions WHERE name = ?", (perm_name,))
            perm_id_row = cursor.fetchone()
        else:
            cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
            perm_id_row = cursor.fetchone()

        if perm_id_row:
            perm_id = perm_id_row[0]
            if is_sqlite:
                cursor.execute(
                    "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                    (role_id, perm_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s) ON CONFLICT (role_id, permission_id) DO NOTHING",
                    (role_id, perm_id),
                )

    # Admin gets all permissions
    for perm_name in permissions_to_add:
        assign_permission(admin_role_id, perm_name)

    # Oficinista permissions
    oficinista_perms = [
        "view_users",
        "manage_users",
        "view_clients",
        "manage_clients",
        "view_services",
        "manage_services",
        "view_freelancers",
        "view_materials",
        "manage_materials",
        "view_proveedores",
        "manage_proveedores",
        "view_financial_reports",
        "view_all_jobs",
        "manage_all_jobs",
        "view_all_tasks",
        "manage_all_tasks",
        "manage_notifications",
        "create_quotes",
        "upload_files",
        "create_new_job", 
    ]
    for perm_name in oficinista_perms:
        assign_permission(oficinista_role_id, perm_name)

    # Autonomo permissions
    autonomo_perms = [
        "view_own_jobs",
        "manage_own_jobs",
        "view_own_tasks",
        "manage_own_tasks",
        "manage_notifications",
        "create_quotes",
        "upload_files",
        "create_new_job",  # Added new permission for adding jobs
    ]
    for perm_name in autonomo_perms:
        assign_permission(autonomo_role_id, perm_name)

    # Client permissions (view own jobs/quotes)
    cliente_perms = ["view_own_jobs", "create_quotes"]  # Clients can create quotes
    for perm_name in cliente_perms:
        assign_permission(cliente_role_id, perm_name)

    # Proveedor permissions
    proveedor_perms = [
        "view_proveedores",
        "upload_files",
    ]
    for perm_name in proveedor_perms:
        assign_permission(proveedor_role_id, perm_name)

    conn.commit()
    cursor.close()
    print("Initialized new database with schema and roles.")
    print("--- Finished setup_new_database ---")


def get_db_connection():
    print(
        "Connecting to SQLite for local development."
    )  # Debug print
    try:  # Added try-except for SQLite connection
        db_path = "database.db"
        db_is_new = not os.path.exists(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        if db_is_new:
            print("SQLite database not found. Initializing new SQLite database...")
            with current_app.app_context():  # Use current_app
                setup_new_database(conn, is_sqlite=True)
            print("SQLite database initialized.")
        return conn, True  # Return connection and is_sqlite=True
    except sqlite3.Error as sqlite_e:  # Catch SQLite errors
        print(f"Error connecting to SQLite: {sqlite_e}")
        import traceback

        traceback.print_exc()  # Print full traceback
        return None, False  # Explicitly return None if SQLite fails


# --- Activity Logging Function ---
def log_activity(user_id, action, details=None):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        print("Error: Could not connect to database for activity logging.")
        return
    cursor = conn.cursor()  # Get a cursor
    timestamp = datetime.now().isoformat()
    
    if is_sqlite:
        cursor.execute(
            "INSERT INTO activity_log (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, action, details, timestamp),
        )
    else:
        cursor.execute(
            "INSERT INTO activity_log (user_id, action, details, timestamp) VALUES (%s, %s, %s, %s)",
            (user_id, action, details, timestamp),
        )  # Use cursor.execute and %s
    conn.commit()
    cursor.close()  # Close cursor
    conn.close()  # Close connection


# --- Notification Generation Function ---
def generate_notifications_for_user(user_id):
    conn, is_sqlite = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # 1. Upcoming Jobs
        if is_sqlite:
            cursor.execute(
                "SELECT id, titulo, fecha_visita FROM trabajos WHERE date(fecha_visita) BETWEEN date(?) AND date(?, '+7 days') AND estado != 'Finalizado'",
                (today, today),
            )
        else:
            cursor.execute(
                "SELECT id, titulo, fecha_visita FROM trabajos WHERE fecha_visita::date BETWEEN date(%s) AND date(%s, '+7 days') AND estado != 'Finalizado'",
                (today, today),
            )
        upcoming_jobs = cursor.fetchall()
        for job in upcoming_jobs:
            message = f"El trabajo '{job['titulo']}' está programado para el {job['fecha_visita']}."
            if is_sqlite:
                cursor.execute(
                    "SELECT id FROM notifications WHERE user_id = ? AND type = 'job_reminder' AND related_id = ? AND message = ?",
                    (user_id, job["id"], message),
                )
            else:
                cursor.execute(
                    "SELECT id FROM notifications WHERE user_id = %s AND type = 'job_reminder' AND related_id = %s AND message = %s",
                    (user_id, job["id"], message),
                )
            if not cursor.fetchone():
                if is_sqlite:
                    cursor.execute(
                        "INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (
                            user_id,
                            message,
                            "job_reminder",
                            job["id"],
                            datetime.now().isoformat(),
                        ),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (%s, %s, %s, %s, %s)",
                        (
                            user_id,
                            message,
                            "job_reminder",
                            job["id"],
                            datetime.now().isoformat(),
                        ),
                    )

        # 2. Overdue Tasks
        if is_sqlite:
            cursor.execute(
                "SELECT t.id, t.titulo, t.fecha_limite, tr.titulo as trabajo_titulo FROM tareas t "
                "JOIN trabajos tr ON t.trabajo_id = tr.id "
                "WHERE t.fecha_limite < ? AND t.estado != 'Completada' AND t.autonomo_id = ?",
                (today, user_id),
            )
        else:
            cursor.execute(
                "SELECT t.id, t.titulo, t.fecha_limite, tr.titulo as trabajo_titulo FROM tareas t "
                "JOIN trabajos tr ON t.trabajo_id = tr.id "
                "WHERE t.fecha_limite < %s AND t.estado != 'Completada' AND t.autonomo_id = %s",
                (today, user_id),
            )
        overdue_tasks = cursor.fetchall()
        for task in overdue_tasks:
            message = f"La tarea '{task['titulo']}' del trabajo '{task['trabajo_titulo']}' está atrasada desde el {task['fecha_limite']}."
            if is_sqlite:
                cursor.execute(
                    "SELECT id FROM notifications WHERE user_id = ? AND type = 'task_overdue' AND related_id = ? AND message = ?",
                    (user_id, task["id"], message),
                )
            else:
                cursor.execute(
                    "SELECT id FROM notifications WHERE user_id = %s AND type = 'task_overdue' AND related_id = %s AND message = %s",
                    (user_id, task["id"], message),
                )
            if not cursor.fetchone():
                if is_sqlite:
                    cursor.execute(
                        "INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (
                            user_id,
                            message,
                            "task_overdue",
                            task["id"],
                            datetime.now().isoformat(),
                        ),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (%s, %s, %s, %s, %s)",
                        (
                            user_id,
                            message,
                            "task_overdue",
                            task["id"],
                            datetime.now().isoformat(),
                        ),
                    )

        # 3. Low Stock Materials
        if is_sqlite:
            cursor.execute(
                "SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = ?",
                (user_id,),
            )
        else:
            cursor.execute(
                "SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = %s",
                (user_id,),
            )
        user_roles = cursor.fetchall()
        role_names = [role["name"] for role in user_roles]

        if "Admin" in role_names or "Oficinista" in role_names:
            if is_sqlite:
                cursor.execute(
                    "SELECT id, name, current_stock, min_stock_level FROM materials WHERE current_stock <= min_stock_level"
                )
            else:
                cursor.execute(
                    "SELECT id, name, current_stock, min_stock_level FROM materials WHERE current_stock <= min_stock_level"
                )
            low_stock_materials = cursor.fetchall()
            for material in low_stock_materials:
                message = f"El material '{material['name']}' tiene bajo stock: {material['current_stock']} (Mínimo: {material['min_stock_level']})."
                if is_sqlite:
                    cursor.execute(
                        "SELECT id FROM notifications WHERE user_id = ? AND type = 'low_stock' AND related_id = ? AND message = ?",
                        (user_id, material["id"], message),
                    )
                else:
                    cursor.execute(
                        "SELECT id FROM notifications WHERE user_id = %s AND type = 'low_stock' AND related_id = %s AND message = %s",
                        (user_id, material["id"], message),
                    )
                if not cursor.fetchone():
                    if is_sqlite:
                        cursor.execute(
                            "INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                            (
                                user_id,
                                message,
                                "low_stock",
                                material["id"],
                                datetime.now().isoformat(),
                            ),
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (%s, %s, %s, %s, %s)",
                            (
                                user_id,
                                message,
                                "low_stock",
                                material["id"],
                                datetime.now().isoformat(),
                            ),
                        )

        conn.commit()
    except sqlite3.Error as e:
        print(f"Error generating notifications: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# --- Database Initialization Command ---
@click.command("init-db")
def init_db_command():
    """Clear the existing data and create new tables with a large set of sample data."""
    db, is_sqlite = get_db_connection()
    if db is None:
        click.echo("Error: Could not connect to database for init-db command.")
        return
    try:
        with current_app.app_context():
            setup_new_database(db, is_sqlite=is_sqlite)
    except Exception as e:
        click.echo(f"Error during database setup: {e}")
        db.rollback()
        return
    finally:
        if db:
            db.close()

    db, is_sqlite = get_db_connection()  # Reopen connection for data insertion
    if db is None:
        click.echo("Error: Could not reconnect to database after schema setup.")
        return
    cursor = db.cursor() # Define cursor here

    # --- Roles ---
    _execute_sql(cursor, "INSERT OR IGNORE INTO roles (name) VALUES (?)", ['Admin'], is_sqlite=is_sqlite)
    _execute_sql(cursor, "INSERT OR IGNORE INTO roles (name) VALUES (?)", ['Oficinista'], is_sqlite=is_sqlite)
    _execute_sql(cursor, "INSERT OR IGNORE INTO roles (name) VALUES (?)", ['Autonomo'], is_sqlite=is_sqlite)
    _execute_sql(cursor, "INSERT OR IGNORE INTO roles (name) VALUES (?)", ['Cliente'], is_sqlite=is_sqlite)
    _execute_sql(cursor, "INSERT OR IGNORE INTO roles (name) VALUES (?)", ['Proveedor'], is_sqlite=is_sqlite)
    db.commit()
    
    if is_sqlite:
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Admin',), is_sqlite=is_sqlite)
        admin_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Oficinista',), is_sqlite=is_sqlite)
        oficinista_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Autonomo',), is_sqlite=is_sqlite)
        autonomo_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Cliente',), is_sqlite=is_sqlite)
        cliente_role_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = ?", ('Proveedor',), is_sqlite=is_sqlite)
        proveedor_role_id = cursor.fetchone()["id"]
    else:
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Admin',), is_sqlite=is_sqlite)
        admin_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Oficinista',), is_sqlite=is_sqlite)
        oficinista_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Autonomo',), is_sqlite=is_sqlite)
        autonomo_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Cliente',), is_sqlite=is_sqlite)
        cliente_role_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM roles WHERE name = %s", ('Proveedor',), is_sqlite=is_sqlite)
        proveedor_role_id = cursor.fetchone()[0]

    # --- Permissions ---
    permissions_to_add = [
        "view_users",
        "manage_users",
        "view_freelancers",
        "view_materials",
        "manage_materials",
        "view_proveedores",
        "manage_proveedores",
        "view_financial_reports",
        "manage_csv_import",
        "view_all_jobs",
        "manage_all_jobs",
        "view_own_jobs",
        "manage_own_jobs",
        "view_all_tasks",
        "manage_all_tasks",
        "view_own_tasks",
        "manage_own_tasks",
        "manage_notifications",
        "create_new_job", # New permission for adding jobs
        "create_quotes", # Added create_quotes permission
        "upload_files", # Added upload_files permission
    ]
    for perm_name in permissions_to_add:
        _execute_sql(cursor, "INSERT OR IGNORE INTO permissions (name) VALUES (?)", [perm_name], is_sqlite=is_sqlite)
    db.commit()

    # Assign permissions to roles
    def assign_permission(role_id, perm_name):
        if is_sqlite:
            _execute_sql(cursor, "SELECT id FROM permissions WHERE name = ?", (perm_name,), is_sqlite=is_sqlite)
            perm_id = cursor.fetchone()["id"]
            _execute_sql(cursor,
                "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                (role_id, perm_id), is_sqlite=is_sqlite
            )
        else:
            _execute_sql(cursor, "SELECT id FROM permissions WHERE name = %s", (perm_name,), is_sqlite=is_sqlite)
            perm_id = cursor.fetchone()[0]
            _execute_sql(cursor,
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s) ON CONFLICT (role_id, permission_id) DO NOTHING",
                (role_id, perm_id), is_sqlite=is_sqlite
            )

    # Admin gets all permissions
    for perm_name in permissions_to_add:
        assign_permission(admin_role_id, perm_name)

    # Oficinista permissions
    oficinista_perms = [
        "view_users",
        "view_freelancers",
        "view_materials",
        "manage_materials",
        "view_proveedores",
        "manage_proveedores",
        "view_financial_reports",
        "view_all_jobs",
        "manage_all_jobs",
        "view_all_tasks",
        "manage_all_tasks",
        "manage_notifications",
        "create_new_job", # Added new permission for adding jobs
        "create_quotes", # Added create_quotes permission
        "upload_files", # Added upload_files permission
    ]
    for perm_name in oficinista_perms:
        assign_permission(oficinista_role_id, perm_name)

    # Autonomo permissions
    autonomo_perms = [
        "view_own_jobs",
        "manage_own_jobs",
        "view_own_tasks",
        "manage_own_tasks",
        "manage_notifications",
        "create_new_job", # Added new permission for adding jobs
        "create_quotes", # Added create_quotes permission
        "upload_files", # Added upload_files permission
    ]
    for perm_name in autonomo_perms:
        assign_permission(autonomo_role_id, perm_name)

    # Cliente permissions
    cliente_perms = ["view_own_jobs", "create_quotes"]
    for perm_name in cliente_perms:
        assign_permission(cliente_role_id, perm_name)

    # Proveedor permissions
    proveedor_perms = [
        "view_proveedores",
        "upload_files",
    ]
    for perm_name in proveedor_perms:
        assign_permission(proveedor_role_id, perm_name)
    db.commit()

    # --- Users ---
    users_to_add = [
        ("jorge moreno", "6336604j", "admin@grupokoal.com", admin_role_id),
        (
            "Laura Ventas",
            "password123",
            "laura.ventas@grupokoal.com",
            oficinista_role_id,
        ),
        ("Carlos Gomez", "password123", "carlos.gomez@autonomo.com", autonomo_role_id),
        ("Sofia Lopez", "password123", "sofia.lopez@autonomo.com", autonomo_role_id),
        ("Ana Torres", "password123", "ana.torres@autonomo.com", autonomo_role_id),
        ("Cliente Ejemplo", "password123", "cliente@ejemplo.com", cliente_role_id),
        ("Proveedor Ejemplo", "password123", "proveedor@ejemplo.com", proveedor_role_id),
    ]
    for username, password, email, role_id in users_to_add:
        hashed_password = generate_password_hash(password)
        _execute_sql(cursor,
            "INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, ?) RETURNING id",
            (username, hashed_password, email, True), is_sqlite=is_sqlite
        )
        user_id = cursor.fetchone()[0] # Get last inserted ID for both SQLite and PostgreSQL
        _execute_sql(cursor,
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id), is_sqlite=is_sqlite
        )
    db.commit()
    
    if is_sqlite:
        _execute_sql(cursor, "SELECT id FROM users WHERE username = ?", ('Carlos Gomez',), is_sqlite=is_sqlite)
        carlos_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM users WHERE username = ?", ('Sofia Lopez',), is_sqlite=is_sqlite)
        sofia_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM users WHERE username = ?", ('Ana Torres',), is_sqlite=is_sqlite)
        ana_id = cursor.fetchone()["id"]
    else:
        _execute_sql(cursor, "SELECT id FROM users WHERE username = %s", ('Carlos Gomez',), is_sqlite=is_sqlite)
        carlos_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM users WHERE username = %s", ('Sofia Lopez',), is_sqlite=is_sqlite)
        sofia_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM users WHERE username = %s", ('Ana Torres',), is_sqlite=is_sqlite)
        ana_id = cursor.fetchone()[0]

    # --- Clients ---
    _execute_sql(cursor,
        "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
        (
            "Constructora XYZ",
            "Calle Falsa 123, Valencia",
            "960123456",
            "contacto@constructoraxyz.com",
        ), is_sqlite=is_sqlite
    )
    _execute_sql(cursor,
        "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
        (
            "Reformas El Sol",
            "Avenida del Puerto 50, Valencia",
            "960987654",
            "info@reformaselsol.es",
        ), is_sqlite=is_sqlite
    )
    _execute_sql(cursor,
        "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
        (
            "Comunidad de Vecinos El Roble",
            "Plaza del Arbol 1, Silla",
            "961231234",
            "admin@roble.com",
        ), is_sqlite=is_sqlite
    )
    _execute_sql(cursor,
        "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
        (
            "ejem. Maria Dolores",
            "Calle Maldiva, 24",
            "666555444",
            "ejemplo@email.com",
        ), is_sqlite=is_sqlite
    )
    db.commit()
    
    if is_sqlite:
        _execute_sql(cursor, "SELECT id FROM clients WHERE nombre = ?", ('Constructora XYZ',), is_sqlite=is_sqlite)
        client1_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM clients WHERE nombre = ?", ('Reformas El Sol',), is_sqlite=is_sqlite)
        client2_id = cursor.fetchone()["id"]
        _execute_sql(cursor, "SELECT id FROM clients WHERE nombre = ?", ('Comunidad de Vecinos El Roble',), is_sqlite=is_sqlite)
        client3_id = cursor.fetchone()["id"]
    else:
        _execute_sql(cursor, "SELECT id FROM clients WHERE nombre = %s", ('Constructora XYZ',), is_sqlite=is_sqlite)
        client1_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM clients WHERE nombre = %s", ('Reformas El Sol',), is_sqlite=is_sqlite)
        client2_id = cursor.fetchone()[0]
        _execute_sql(cursor, "SELECT id FROM clients WHERE nombre = %s", ('Comunidad de Vecinos El Roble',), is_sqlite=is_sqlite)
        client3_id = cursor.fetchone()[0]

    # --- Proveedores ---
    proveedores_to_add = [
        (
            "Suministros Eléctricos del Turia",
            "Ana García",
            "963123456",
            "info@electricidadturia.com",
            "Calle de la Luz 10, Valencia",
            "Electricidad",
        ),
        (
            "Fontanería Express SL",
            "Pedro Ruiz",
            "963987654",
            "contacto@fontaneriaexpress.es",
            "Av. del Agua 5, Valencia",
            "Fontanería",
        ),
        (
            "Almacenes de Construcción Levante",
            "Marta Pérez",
            "960112233",
            "ventas@almaceneslevante.com",
            "Pol. Ind. La Paz, Valencia",
            "Materiales de Construcción",
        ),
        (
            "Herramientas Profesionales Vlc",
            "Luis Torres",
            "963554433",
            "pedidos@herramientasvlc.com",
            "C/ Herramientas 22, Valencia",
            "Herramientas",
        ),
        (
            "Pinturas Color Vivo",
            "Elena Sanz",
            "963778899",
            "info@pinturascolorvivo.com",
            "Gran Vía 15, Valencia",
            "Pintura",
        ),
        (
            "Climatización Total",
            "Javier Mora",
            "963210987",
            "comercial@climatizaciontotal.com",
            "C/ Aire 3, Valencia",
            "Climatización",
        ),
        (
            "Cristalería Rápida",
            "Carmen Díaz",
            "963445566",
            "presupuestos@cristaleriarapida.com",
            "Av. del Cristal 1, Valencia",
            "Cristalería",
        ),
        (
            "Carpintería Artesanal",
            "Roberto Gil",
            "963667788",
            "info@carpinteriaartesanal.com",
            "C/ Madera 7, Valencia",
            "Carpintería",
        ),
        (
            "Cerrajeros 24h",
            "Sofía Navarro",
            "963889900",
            "urgencias@cerrajeros24h.com",
            "C/ Llave 1, Valencia",
            "Cerrajería",
        ),
        (
            "Reformas Integrales Valencia",
            "Miguel Ángel",
            "963112233",
            "info@reformasin.com",
            "C/ Obra 5, Valencia",
            "Reformas",
        ),
    ]
    for nombre, contacto, telefono, email, direccion, tipo in proveedores_to_add:
        _execute_sql(cursor,
            "INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, contacto, telefono, email, direccion, tipo), is_sqlite=is_sqlite
        )
    _execute_sql(cursor,
        "INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "ejem. Ferreteria La Esquina",
            "Juan Perez",
            "960000000",
            "info@ferreteria.com",
            "Calle de la Ferreteria 1, Valencia",
            "Ferreteria",
        ), is_sqlite=is_sqlite
    )

    # --- Materials & Services ---
    materials_to_add = [
        ("Tornillos 5mm", "Caja de 100 unidades", 20, 5.50, 6.00, 5.00),
        ("Placa de Pladur", "Placa de 120x80cm", 20, 12.75, 13.50, 12.00),
        ("Saco de Cemento", "Saco de 25kg", 20, 8.00, 8.50, 7.80),
        ("Pintura Blanca (10L)", "Pintura plástica interior", 20, 45.00, 48.00, 42.00),
        ("Brocha (50mm)", "Brocha para pintura", 20, 7.50, 8.00, 7.00),
        ("Cable Eléctrico (100m)", "Cable unifilar 2.5mm", 20, 60.00, 65.00, 58.00),
        ("Enchufe Doble", "Enchufe de pared doble", 20, 3.20, 3.50, 3.00),
        ("Tubería PVC (3m)", "Tubería de desagüe 50mm", 20, 15.00, 16.00, 14.50),
        ("Grifo Monomando", "Grifo para lavabo", 20, 35.00, 38.00, 33.00),
        ("Azulejo Blanco (m2)", "Azulejo cerámico 30x30cm", 20, 18.00, 19.00, 17.50),
        ("Silicona (tubo)", "Sellador multiusos", 20, 4.50, 5.00, 4.20),
        ("Martillo", "Martillo de uña", 20, 12.00, 13.00, 11.50),
        ("Taladro Percutor", "Taladro con función percutora", 20, 85.00, 90.00, 80.00),
        ("Lija (paquete)", "Paquete de lijas grano 120", 20, 6.00, 6.50, 5.80),
        ("Guantes de Trabajo", "Guantes de protección", 20, 3.00, 3.20, 2.80),
        ("Masilla para Madera", "Masilla reparadora", 20, 9.00, 9.50, 8.80),
        ("Cinta Aislante", "Cinta aislante eléctrica", 20, 2.50, 2.80, 2.30),
        ("Nivel (60cm)", "Nivel de burbuja", 20, 25.00, 27.00, 24.00),
        (
            "Sierra de Calar",
            "Sierra eléctrica para cortes curvos",
            20,
            55.00,
            58.00,
            52.00,
        ),
        (
            "Destornillador Set",
            "Set de destornilladores variados",
            20,
            18.00,
            19.00,
            17.00,
        ),
    ]
    for (
        name,
        desc,
        stock,
        price,
        recommended_price,
        last_sold_price,
    ) in materials_to_add:
        _execute_sql(cursor,
            "INSERT INTO materials (name, description, current_stock, unit_price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?, ?)",
            (name, desc, stock, price, recommended_price, last_sold_price), is_sqlite=is_sqlite
        )
    _execute_sql(cursor,
        "INSERT INTO materials (name, description, current_stock, unit_price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?, ?)",
        ("ejem. Martillo (Hammer)", "Martillo de carpintero (Carpenter's hammer)", 10, 15.00, 18.00, 14.00), is_sqlite=is_sqlite
    )

    _execute_sql(cursor,
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?)", ('Instalación Eléctrica', 'Punto de luz completo', 50.00, 55.00, 48.00), is_sqlite=is_sqlite
    )
    _execute_sql(cursor,
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?)", ('Fontanería', 'Instalación de grifo', 40.00, 45.00, 38.00), is_sqlite=is_sqlite
    )
    _execute_sql(cursor,
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?)", ('Ejem_Servicio de Pintura', 'Pintura de pared interior', 30.00, 35.00, 28.00), is_sqlite=is_sqlite
    )
    _execute_sql(cursor,
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?)", ('Ejem_Servicio de Albañilería', 'Reparación de muro', 70.00, 75.00, 68.00), is_sqlite=is_sqlite
    )
    _execute_sql(cursor,
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?)", ('ejem. Fontaneria (Plumbing)', 'Instalacion de grifo (Faucet installation)', 50.00, 55.00, 48.00), is_sqlite=is_sqlite
    )

    # --- Trabajos (Jobs) ---
    # --- Trabajos (Jobs) ---
    from datetime import date, timedelta
    import random

    today = date.today()

    # Insert a specific example job first to get its ID
    _execute_sql(cursor,
        "INSERT INTO trabajos (client_id, autonomo_id, titulo, descripcion, estado, presupuesto, vat_rate, fecha_visita, job_difficulty_rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            client1_id,
            carlos_id,
            "Ejem_Reparación eléctrica en obra",
            "Revisar cuadro eléctrico principal (Ejemplo)",
            "En Progreso",
            500.00,
            21.0,
            (today + timedelta(days=2)).isoformat(),
            3,
        ), is_sqlite=is_sqlite
    )
    ejem_job_id = cursor.lastrowid if is_sqlite else cursor.fetchone()[0]

    _execute_sql(cursor,
        "INSERT INTO trabajos (client_id, autonomo_id, titulo, descripcion, estado, presupuesto, vat_rate, fecha_visita, job_difficulty_rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            client1_id,
            carlos_id,
            "ejem. Reparacion de persiana (ejem. Shutter repair)",
            "La persiana del dormitorio no baja (The bedroom shutter does not go down)",
            "Pendiente",
            100.00,
            21.0,
            (today + timedelta(days=5)).isoformat(),
            2,
        ), is_sqlite=is_sqlite
    )

    jobs_to_add = [
        (
            client2_id,
            sofia_id,
            "Instalación de 3 grifos",
            "Baño y cocina de la reforma",
            "Pendiente",
            5,
            random.randint(1, 5),
        ),
        (
            client1_id,
            None,
            "Pintar oficina",
            "Pintar paredes de oficina de 20m2",
            "Presupuestado",
            10,
            random.randint(1, 5),
        ),
        (
            client3_id,
            ana_id,
            "Cambio de bajante",
            "Sustituir bajante comunitaria",
            "Pendiente",
            3,
            random.randint(1, 5),
        ),
        (
            client2_id,
            carlos_id,
            "Instalar 5 puntos de luz",
            "Nuevos puntos en falso techo",
            "En Progreso",
            1,
            random.randint(1, 5),
        ),
        (
            client1_id,
            sofia_id,
            "Revisión fontanería (URGENTE)",
            "Fuga en baño de planta 2",
            "En Progreso",
            -2,
            random.randint(1, 5),
        ),
        (
            client3_id,
            None,
            "Presupuesto reforma portal",
            "Medir y evaluar estado",
            "Presupuestado",
            -5,
            random.randint(1, 5),
        ),
        (
            client2_id,
            ana_id,
            "Alicatado de baño",
            "Poner azulejos en pared de ducha",
            "Finalizado",
            -15,
            random.randint(1, 5),
        ),
        (
            client1_id,
            carlos_id,
            "Instalación de aire acondicionado",
            "Split en salón principal",
            "Finalizado",
            -30,
            random.randint(1, 5),
        ),
        (
            client3_id,
            sofia_id,
            "Reparar persiana",
            "La persiana del dormitorio no baja",
            "Pendiente",
            7,
            random.randint(1, 5),
        ),
        (
            client1_id,
            ana_id,
            "Mantenimiento ascensor",
            "Revisión mensual programada",
            "Pendiente",
            12,
            random.randint(1, 5),
        ),
        (
            client2_id,
            None,
            "Presupuesto pintura exterior",
            "Evaluar fachada y medir metros",
            "Presupuestado",
            4,
            random.randint(1, 5),
        ),
        (
            client3_id,
            carlos_id,
            "Solucionar apagón",
            "El diferencial salta constantemente",
            "En Progreso",
            0,
            random.randint(1, 5),
        ),
        (
            client1_id,
            sofia_id,
            "Cambiar cisterna",
            "La cisterna del baño de invitados pierde agua",
            "Pendiente",
            8,
            random.randint(1, 5),
        ),
        (
            client2_id,
            ana_id,
            "Instalar tarima flotante",
            "Habitación de 15m2",
            "Presupuestado",
            20,
            random.randint(1, 5),
        ),
        (
            client3_id,
            carlos_id,
            "Revisión de gas",
            "Inspección periódica obligatoria",
            "Finalizado",
            -45,
            random.randint(1, 5),
        ),
        (
            client1_id,
            None,
            "Limpieza de obra",
            "Retirar escombros y limpiar zona",
            "Pendiente",
            6,
            random.randint(1, 5),
        ),
        (
            client2_id,
            sofia_id,
            "Montaje de muebles de cocina",
            "Montar 4 módulos y encimera",
            "En Progreso",
            1,
            random.randint(1, 5),
        ),
        (
            client3_id,
            ana_id,
            "Reparación de goteras",
            "Goteras en el techo del ático",
            "Pendiente",
            9,
            random.randint(1, 5),
        ),
        (
            client1_id,
            carlos_id,
            "Instalar videoportero",
            "Sustituir telefonillo antiguo",
            "Finalizado",
            -10,
            random.randint(1, 5),
        ),
        (
            client1_id,
            carlos_id,
            "Revisión instalación gas",
            "Inspección anual obligatoria",
            "Pendiente",
            15,
            random.randint(1, 5),
        ),
        (
            client2_id,
            sofia_id,
            "Reparación tejado",
            "Sustitución de tejas rotas",
            "Presupuestado",
            25,
            random.randint(1, 5),
        ),
        (
            client3_id,
            ana_id,
            "Instalación de alarma",
            "Sistema de seguridad para vivienda",
            "En Progreso",
            3,
            random.randint(1, 5),
        ),
        (
            client1_id,
            None,
            "Presupuesto reforma cocina",
            "Diseño y presupuesto de cocina",
            "Presupuestado",
            18,
            random.randint(1, 5),
        ),
        (
            client2_id,
            carlos_id,
            "Desatasco de tubería",
            "Desatasco en baño principal",
            "Finalizado",
            -1,
            random.randint(1, 5),
        ),
        (
            client3_id,
            sofia_id,
            "Cambio de cerradura",
            "Sustitución de bombín de seguridad",
            "Pendiente",
            10,
            random.randint(1, 5),
        ),
        (
            client1_id,
            ana_id,
            "Instalación de termo eléctrico",
            "Sustitución de termo antiguo",
            "En Progreso",
            0,
            random.randint(1, 5),
        ),
        (
            client2_id,
            None,
            "Revisión de caldera",
            "Mantenimiento preventivo",
            "Pendiente",
            22,
            random.randint(1, 5),
        ),
        (
            client3_id,
            carlos_id,
            "Montaje de pérgola",
            "Instalación de pérgola en terraza",
            "Finalizado",
            -7,
            random.randint(1, 5),
        ),
        (
            client1_id,
            sofia_id,
            "Reparación de gotera en techo",
            "Localizar y reparar origen de gotera",
            "En Progreso",
            -3,
            random.randint(1, 5),
        ),
        (
            client2_id,
            ana_id,
            "Instalación de suelo laminado",
            "Salón de 30m2",
            "Presupuestado",
            28,
            random.randint(1, 5),
        ),
        (
            client3_id,
            None,
            "Presupuesto instalación placas solares",
            "Estudio de viabilidad",
            "Pendiente",
            14,
            random.randint(1, 5),
        ),
        (
            client1_id,
            carlos_id,
            "Revisión de extintores",
            "Mantenimiento anual",
            "Finalizado",
            -60,
            random.randint(1, 5),
        ),
        (
            client2_id,
            sofia_id,
            "Reparación de puerta de garaje",
            "Ajuste de motor y guías",
            "En Progreso",
            -10,
            random.randint(1, 5),
        ),
        (
            client3_id,
            ana_id,
            "Instalación de antena TV",
            "Antena parabólica para canales satélite",
            "Pendiente",
            11,
            random.randint(1, 5),
        ),
        (
            client1_id,
            None,
            "Limpieza de cristales en altura",
            "Edificio de oficinas",
            "Presupuestado",
            19,
            random.randint(1, 5),
        ),
        (
            client2_id,
            carlos_id,
            "Reparación de bomba de agua",
            "Bomba de pozo",
            "En Progreso",
            -20,
            random.randint(1, 5),
        ),
        (
            client3_id,
            sofia_id,
            "Instalación de mampara de ducha",
            "Mampara de cristal templado",
            "Finalizado",
            -5,
            random.randint(1, 5),
        ),
        (
            client1_id,
            ana_id,
            "Revisión de sistema de riego",
            "Jardín comunitario",
            "Pendiente",
            25,
            random.randint(1, 5),
        ),
        (
            client2_id,
            None,
            "Presupuesto reforma integral",
            "Vivienda de 90m2",
            "Presupuestado",
            30,
            random.randint(1, 5),
        ),
    ]
    for client, autonomo, titulo, desc, estado, delta, difficulty in jobs_to_add:
        fecha = today + timedelta(days=delta)
        presupuesto = round(random.uniform(100, 2000), 2)
        _execute_sql(cursor,
            "INSERT INTO trabajos (client_id, autonomo_id, titulo, descripcion, estado, presupuesto, fecha_visita, job_difficulty_rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                client,
                autonomo,
                titulo,
                desc,
                estado,
                presupuesto,
                fecha.isoformat(),
                difficulty,
            ), is_sqlite=is_sqlite
        )

    

    db.commit()

    # --- Tareas (Tasks) ---
    # Get an existing job_id to link tasks to
    if is_sqlite:
        _execute_sql(cursor, "SELECT id FROM users WHERE username = ?", ('Carlos Gomez',), is_sqlite=is_sqlite)
        ejem_autonomo_id = cursor.fetchone()["id"]
    else:
        _execute_sql(cursor, "SELECT id FROM users WHERE username = %s", ('Carlos Gomez',), is_sqlite=is_sqlite)
        ejem_autonomo_id = cursor.fetchone()[0]

    tareas_to_add = [
        (
            ejem_job_id,
            "Ejem_Revisar cableado",
            "Revisión completa del cableado principal.",
            "En Progreso",
            (today + timedelta(days=3)).isoformat(),
            ejem_autonomo_id,
            "Tarjeta",
            "Abonado",
            50.00,
            (today + timedelta(days=1)).isoformat(),
        ),
        (
            ejem_job_id,
            "ejem. Comprar lamas (Buy slats)",
            "Comprar lamas de persiana (Buy shutter slats)",
            "Pendiente",
            (today + timedelta(days=4)).isoformat(),
            ejem_autonomo_id,
            "Efectivo",
            "Pendiente",
            0.00,
            None,
        ),
    ]
    for (
        trabajo_id,
        titulo,
        descripcion,
        estado,
        fecha_limite,
        autonomo_id,
        metodo_pago,
        estado_pago,
        monto_abonado,
        fecha_pago,
    ) in tareas_to_add:
        _execute_sql(cursor,
            "INSERT INTO tareas (trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                trabajo_id,
                titulo,
                descripcion,
                estado,
                fecha_limite,
                autonomo_id,
                metodo_pago,
                estado_pago,
                monto_abonado,
                fecha_pago,
            ), is_sqlite=is_sqlite
        )

    

    db.commit()
    db.close()
    click.echo("Base de datos inicializada con un gran conjunto de datos de ejemplo.")


app.cli.add_command(init_db_command)


@click.command("import-csv-data")
def import_csv_data_command():
    """Import data from CSV files into the database."""
    db, is_sqlite = get_db_connection()
    if db is None:
        click.echo("Error: Could not connect to database for CSV import.")
        return

    # Define base directory for CSVs relative to app root
    csv_base_dir = os.path.join(
        current_app.root_path, "datos de distribuidores y autonomos"
    )

    # --- Import Autonomos (Users) ---
    autonomos_csv_path = os.path.join(
        csv_base_dir, "autonomos_y_servicios_valencia.csv"
    )
    try:
        with db.cursor() as cursor:  # Use cursor for all db operations
            

            with open(autonomos_csv_path, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                _execute_sql(cursor, "SELECT id FROM roles WHERE name = 'Autonomo'", is_sqlite=is_sqlite)
                autonomo_role_id = cursor.fetchone()["id"]
                for row in reader:
                    username = row["Nombre"].strip()
                    email = (
                        row["Email"].strip()
                        if row["Email"].strip()
                        else f"{username.replace(' ', '.').lower()}@autonomo.com"
                    )
                    password = "password123"  # Default password
                    hashed_password = generate_password_hash(password)

                    # Check if user already exists
                    _execute_sql(cursor, "SELECT id FROM users WHERE username = ? OR email = ?", (username, email), is_sqlite=is_sqlite)
                    existing_user = cursor.fetchone()
                    if not existing_user:
                        _execute_sql(cursor, "INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, ?)", (username, hashed_password, email, True), is_sqlite=is_sqlite)
                        _execute_sql(cursor, "SELECT last_insert_rowid()", is_sqlite=is_sqlite)
                        user_id = cursor.fetchone()[0]
                        _execute_sql(cursor, "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, autonomo_role_id), is_sqlite=is_sqlite)

                        # Insert into freelancer_details
                        _execute_sql(cursor, "INSERT INTO freelancer_details (id, category, specialty, city_province, address, web, phone, whatsapp, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                                user_id,
                                row["Categoria"].strip(),
                                row["Especialidad"].strip(),
                                row["Ciudad/Provincia"].strip(),
                                row["Direccion"].strip(),
                                row["Web"].strip(),
                                row["Telefono"].strip(),
                                row["WhatsApp"].strip(),
                                row["Notas"].strip(),
                                row["FuenteURL"].strip(),
                                0.0,  # Default normal rate
                                0.0,  # Default tier2 rate
                                0.0,  # Default tier3 rate
                                5.0,  # Example difficulty surcharge rate
                            ), is_sqlite=is_sqlite)
                        click.echo(f"Imported autonomo: {username}")
                    else:
                        click.echo(f"Autonomo already exists (skipped): {username}")
            db.commit()
            click.echo("Autonomos imported successfully.")
    except FileNotFoundError:
        click.echo(f"Error: Autonomos CSV file not found at {autonomos_csv_path}")
    except Exception as e:
        click.echo(f"Error importing autonomos: {e}")
        db.rollback()

    # --- Import Proveedores ---
    proveedores_dir = csv_base_dir  # Use the defined base directory
    proveedores_files = [
        f
        for f in os.listdir(proveedores_dir)
        if f.startswith("proveedores_") and f.endswith(".csv")
    ]

    for p_file in proveedores_files:
        p_file_path = os.path.join(proveedores_dir, p_file)
        try:
            with db.cursor() as cursor:  # Use cursor for all db operations

                with open(p_file_path, mode="r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        nombre = row["Nombre"].strip()
                        contacto = (
                            row["Especialidad"].strip()
                            if row["Especialidad"].strip()
                            else ""
                        )
                        telefono = row["Telefono"].strip()
                        email = row["Email"].strip()
                        direccion = row["Direccion"].strip()
                        tipo = row["Categoria"].strip()

                        # Check if proveedor already exists
                        _execute_sql(cursor, "SELECT id FROM proveedores WHERE nombre = ?", (nombre,), is_sqlite=is_sqlite)
                        existing_proveedor = cursor.fetchone()
                        if not existing_proveedor:
                            _execute_sql(cursor, "INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)", (nombre, contacto, telefono, email, direccion, tipo), is_sqlite=is_sqlite)
                            click.echo(f"Imported proveedor: {nombre} from {p_file}")
                        else:
                            click.echo(
                                f"Proveedor already exists (skipped): {nombre} from {p_file}"
                            )
                db.commit()
        except FileNotFoundError:
            click.echo(f"Error: Proveedor CSV file not found at {p_file_path}")
        except Exception as e:
            click.echo(f"Error importing proveedores from {p_file}: {e}")
            db.rollback()

    # --- Import Service Recommended Prices ---
    market_study_dir = csv_base_dir  # Use the defined base directory
    market_study_files = [
        "grupokoal_PRICEBOOK_recomendado_Valencia_2025.csv",
        "grupokoal_estudio_mercado_precios_valencia_2025.csv",
    ]

    for ms_file_name in market_study_files:
        ms_file_path = os.path.join(market_study_dir, ms_file_name)
        try:
            with db.cursor() as cursor:  # Use cursor for all db operations

                with open(ms_file_path, mode="r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        service_name = row["Servicio"].strip()
                        # Use Precio_objetivo for recommended_price
                        recommended_price = (
                            float(row["Precio_objetivo"])
                            if "Precio_objetivo" in row and row["Precio_objetivo"]
                            else 0.0
                        )

                        # Update the service in the database
                        _execute_sql(cursor, "UPDATE services SET recommended_price = ? WHERE name = ?", (recommended_price, service_name), is_sqlite=is_sqlite)
                        if cursor.rowcount > 0:
                            click.echo(
                                f"Updated recommended price for service: {service_name} from {ms_file_name}"
                            )
                        # else:
                        #     click.echo(f"Service not found for recommended price update: {service_name} from {ms_file_name}")
                db.commit()
        except FileNotFoundError:
            click.echo(f"Error: Market study CSV file not found at {ms_file_path}")
        except Exception as e:
            click.echo(f"Error importing market study data from {ms_file_name}: {e}")
            db.rollback()

    db.close()
    click.echo("CSV data import process completed.")


app.cli.add_command(import_csv_data_command)

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, id, username, password_hash, email, is_active):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self._is_active = is_active
        self._permissions = None

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self._is_active

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name):
        if self._permissions is None:
            self._load_permissions()
        return permission_name in self._permissions

    def _load_permissions(self):
        conn, is_sqlite = get_db_connection()
        if not conn:
            self._permissions = set()
            return

        self._permissions = set()
        cursor = conn.cursor() # Fix: Assign cursor directly
        try:
            if is_sqlite:
                cursor.execute(
                    "SELECT p.name FROM permissions p JOIN role_permissions rp ON p.id = rp.permission_id JOIN user_roles ur ON rp.role_id = ur.role_id WHERE ur.user_id = ?", (self.id,)
                )
            else:
                cursor.execute(
                    "SELECT p.name FROM permissions p JOIN role_permissions rp ON p.id = rp.permission_id JOIN user_roles ur ON rp.role_id = ur.role_id WHERE ur.user_id = %s", (self.id,)
                )
            permissions = cursor.fetchall()
            for row in permissions:
                self._permissions.add(row[0])
        except Exception as e:
            print(f"Error loading permissions: {e}")
        finally:
            if cursor: # Ensure cursor is closed
                cursor.close()
            if conn:
                conn.close()


@login_manager.user_loader
def load_user(user_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        print("Error: Could not connect to database for user loading.")
        return None  # Return None if connection fails
    cursor = conn.cursor()  # Get a cursor
    _execute_sql(cursor, "SELECT * FROM users WHERE id = ?", (user_id,), is_sqlite=is_sqlite)
    user_data = cursor.fetchone()  # Fetch from cursor
    cursor.close()  # Close cursor
    conn.close()  # Close connection
    if user_data:
        return User(
            user_data["id"],
            user_data["username"],
            user_data["password_hash"],
            user_data["email"],
            user_data["is_active"],
        )
    return None


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/about")
def about():
    return render_template("about.html")


# --- Authentication Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn, is_sqlite = get_db_connection()
        if conn is None:
            flash("Error: No se pudo conectar a la base de datos.", "danger")
            return render_template("login.html")  # Return to login page with error

        cursor = conn.cursor()  # Get a cursor
        _execute_sql(cursor, "SELECT * FROM users WHERE username = ?", (username,), is_sqlite=is_sqlite)
        user_data = cursor.fetchone()  # Fetch from cursor
        cursor.close()  # Close cursor
        conn.close()  # Close connection

        if user_data:
            user = User(
                user_data["id"],
                user_data["username"],
                user_data["password_hash"],
                user_data["email"],
                user_data["is_active"],
            )
            if user.check_password(password):
                login_user(user)
                flash("Inicio de sesión exitoso.", "success")
                log_activity(user.id, "LOGIN", f"User {user.username} logged in.")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard"))

        flash("Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    log_activity(current_user.id, "LOGOUT", f"User {current_user.username} logged out.")
    logout_user()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("login"))
    cursor = conn.cursor()

    # Fetch upcoming jobs for the dashboard
    upcoming_jobs = []
    # Fetch job statistics
    stats = {}
    # Initialize today_workload
    today_workload = 0
    # Initialize tomorrow_workload
    tomorrow_workload = 0
    try:
        if current_user.has_permission("view_all_jobs"):
            _execute_sql(cursor, "SELECT t.id, t.titulo, t.fecha_visita, c.nombre as client_name, u.username as autonomo_name FROM trabajos t JOIN clients c ON t.client_id = c.id LEFT JOIN users u ON t.autonomo_id = u.id WHERE t.estado != 'Finalizado' ORDER BY t.fecha_visita ASC LIMIT 5", is_sqlite=is_sqlite)
            upcoming_jobs = cursor.fetchall()

            # Fetch job counts by status for all jobs
            _execute_sql(cursor, "SELECT estado, COUNT(*) FROM trabajos GROUP BY estado", is_sqlite=is_sqlite)
            job_counts = cursor.fetchall()
            for row in job_counts:
                stats[row['estado']] = row['COUNT(*)'] # Access by column name
        elif current_user.has_permission("view_own_jobs"):
            _execute_sql(cursor, "SELECT t.id, t.titulo, t.fecha_visita, c.nombre as client_name, u.username as autonomo_name FROM trabajos t JOIN clients c ON t.client_id = c.id LEFT JOIN users u ON t.autonomo_id = u.id WHERE t.autonomo_id = ? AND t.estado != 'Finalizado' ORDER BY t.fecha_visita ASC LIMIT 5", (current_user.id,), is_sqlite=is_sqlite)
            upcoming_jobs = cursor.fetchall()

            # Fetch job counts by status for own jobs
            _execute_sql(cursor, "SELECT estado, COUNT(*) FROM trabajos WHERE autonomo_id = ? GROUP BY estado", (current_user.id,), is_sqlite=is_sqlite)
            job_counts = cursor.fetchall()
            for row in job_counts:
                stats[row['estado']] = row['COUNT(*)'] # Access by column name
        
        # Calculate today_workload
        today = datetime.now().strftime("%Y-%m-%d")
        _execute_sql(cursor, "SELECT COUNT(*) FROM tareas WHERE autonomo_id = ? AND fecha_limite = ?", (current_user.id, today), is_sqlite=is_sqlite)
        workload_row = cursor.fetchone()
        if workload_row:
            today_workload = workload_row[0]

        # Calculate tomorrow_workload
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        _execute_sql(cursor, "SELECT COUNT(*) FROM tareas WHERE autonomo_id = ? AND fecha_limite = ?", (current_user.id, tomorrow), is_sqlite=is_sqlite)
        tomorrow_workload_row = cursor.fetchone()
        if tomorrow_workload_row:
            tomorrow_workload = tomorrow_workload_row[0]

    except Exception as e:
        flash(f"Error al cargar datos del dashboard: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("dashboard.html", upcoming_jobs=upcoming_jobs, stats=stats, today_workload=today_workload, tomorrow_workload=tomorrow_workload)


@app.route("/trabajos")
@login_required
@permission_required("view_all_jobs") # Or view_own_jobs
def list_trabajos():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    trabajos = []
    try:
        if current_user.has_permission("view_all_jobs"):
            cursor.execute("SELECT t.id, t.titulo, t.descripcion, t.estado, t.presupuesto, t.fecha_visita, c.nombre as client_name, u.username as autonomo_name FROM trabajos t JOIN clients c ON t.client_id = c.id LEFT JOIN users u ON t.autonomo_id = u.id ORDER BY t.fecha_visita DESC")
        elif current_user.has_permission("view_own_jobs"):
            cursor.execute("SELECT t.id, t.titulo, t.descripcion, t.estado, t.presupuesto, t.fecha_visita, c.nombre as client_name, u.username as autonomo_name FROM trabajos t JOIN clients c ON t.client_id = c.id LEFT JOIN users u ON t.autonomo_id = u.id WHERE t.autonomo_id = %s ORDER BY t.fecha_visita DESC", (current_user.id,))
        trabajos = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar trabajos: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return render_template("trabajos/list.html", trabajos=trabajos)


@app.route("/trabajos/add", methods=["GET", "POST"])
@login_required
@permission_required("create_new_job")
def add_trabajo():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    clients = []
    autonomos = []
    try:
        cursor = conn.cursor()
        _execute_sql(cursor, "SELECT id, nombre FROM clients ORDER BY nombre", is_sqlite=is_sqlite)
        clients = cursor.fetchall()
        _execute_sql(cursor, "SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'Autonomo' ORDER BY u.username", is_sqlite=is_sqlite)
        autonomos = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar datos para el formulario: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_trabajos"))

    if request.method == "POST":
        client_id = request.form["client_id"]
        autonomo_id = request.form.get("autonomo_id")
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        estado = request.form["estado"]
        presupuesto = request.form.get("presupuesto")
        vat_rate = request.form.get("vat_rate")
        fecha_visita = request.form.get("fecha_visita")
        job_difficulty_rating = request.form.get("job_difficulty_rating")

        if not all([client_id, titulo, descripcion, estado]):
            flash("Por favor, completa todos los campos obligatorios.", "danger")
            if conn: conn.close()
            return render_template("trabajos/form.html", title="Añadir Trabajo", clients=clients, autonomos=autonomos)

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO trabajos (client_id, autonomo_id, titulo, descripcion, estado, presupuesto, vat_rate, fecha_visita, job_difficulty_rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (client_id, autonomo_id if autonomo_id else None, titulo, descripcion, estado, presupuesto if presupuesto else None, vat_rate if vat_rate else None, fecha_visita if fecha_visita else None, job_difficulty_rating if job_difficulty_rating else None),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Trabajo añadido exitosamente.", "success")
            log_activity(current_user.id, "ADD_JOB", f"Added job: {titulo} for client {client_id}.")
            return redirect(url_for("list_trabajos"))
        except Exception as e:
            flash(f"Error al añadir trabajo: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    # Pass an empty trabajo object for the form to render correctly
    trabajo = {
        'client_id': '', 'autonomo_id': '', 'titulo': '', 'descripcion': '',
        'estado': 'Pendiente', 'presupuesto': '', 'vat_rate': '21.0',
        'fecha_visita': '', 'job_difficulty_rating': ''
    }
    return render_template("trabajos/form.html", title="Añadir Trabajo", clients=clients, autonomos=autonomos, trabajo=trabajo)


@app.route("/trabajos/edit/<int:trabajo_id>", methods=["GET", "POST"])
@login_required
@permission_required("manage_all_jobs") # Or manage_own_jobs
def edit_trabajo(trabajo_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    trabajo = None
    clients = []
    autonomos = []
    try:
        _execute_sql(cursor, "SELECT * FROM trabajos WHERE id = ?", (trabajo_id,), is_sqlite=is_sqlite)
        trabajo = cursor.fetchone()
        if not trabajo:
            flash("Trabajo no encontrado.", "danger")
            return redirect(url_for("list_trabajos"))

        _execute_sql(cursor, "SELECT id, nombre FROM clients ORDER BY nombre", is_sqlite=is_sqlite)
        clients = cursor.fetchall()
        _execute_sql(cursor, "SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'Autonomo' ORDER BY u.username", is_sqlite=is_sqlite)
        autonomos = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar datos para el formulario: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_trabajos"))

    if request.method == "POST":
        client_id = request.form["client_id"]
        autonomo_id = request.form.get("autonomo_id")
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        estado = request.form["estado"]
        presupuesto = request.form.get("presupuesto")
        vat_rate = request.form.get("vat_rate")
        fecha_visita = request.form.get("fecha_visita")
        job_difficulty_rating = request.form.get("job_difficulty_rating")

        if not all([client_id, titulo, descripcion, estado]):
            flash("Por favor, completa todos los campos obligatorios.", "danger")
            return render_template("trabajos/form.html", title="Editar Trabajo", trabajo=trabajo, clients=clients, autonomos=autonomos)

        try:
            _execute_sql(cursor,
                "UPDATE trabajos SET client_id = ?, autonomo_id = ?, titulo = ?, descripcion = ?, estado = ?, presupuesto = ?, vat_rate = ?, fecha_visita = ?, job_difficulty_rating = ? WHERE id = ?",
                (client_id, autonomo_id if autonomo_id else None, titulo, descripcion, estado, presupuesto if presupuesto else None, vat_rate if vat_rate else None, fecha_visita if fecha_visita else None, job_difficulty_rating if job_difficulty_rating else None, trabajo_id),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Trabajo actualizado exitosamente.", "success")
            log_activity(current_user.id, "EDIT_JOB", f"Edited job: {titulo} (ID: {trabajo_id}).")
            return redirect(url_for("list_trabajos"))
        except Exception as e:
            flash(f"Error al actualizar trabajo: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("trabajos/form.html", title="Editar Trabajo", trabajo=trabajo, clients=clients, autonomos=autonomos)


@app.route("/materials")
@login_required
@permission_required("view_materials")
def list_materials():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    materials = []
    try:
        _execute_sql(cursor, "SELECT * FROM materials ORDER BY name ASC", is_sqlite=is_sqlite)
        materials = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar materiales: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("materials/list.html", materials=materials)


@app.route("/materials/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_materials")
def add_material():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description")
        current_stock = request.form.get("current_stock", type=int)
        unit_price = request.form.get("unit_price", type=float)
        min_stock_level = request.form.get("min_stock_level", type=int)
        unit_of_measure = request.form.get("unit_of_measure")

        if not all([name, current_stock is not None, unit_price is not None, min_stock_level is not None]):
            flash("Por favor, completa todos los campos obligatorios.", "danger")
            return render_template("materials/form.html", title="Añadir Material")

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO materials (name, description, current_stock, unit_price, min_stock_level, unit_of_measure) VALUES (?, ?, ?, ?, ?, ?)",
                (name, description, current_stock, unit_price, min_stock_level, unit_of_measure),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Material añadido exitosamente.", "success")
            log_activity(current_user.id, "ADD_MATERIAL", f"Added material: {name}.")
            return redirect(url_for("list_materials"))
        except Exception as e:
            flash(f"Error al añadir material: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("materials/form.html", title="Añadir Material")


@app.route("/stock_movements/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_materials")
def add_stock_movement():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    materials = []
    try:
        cursor = conn.cursor()
        _execute_sql(cursor, "SELECT id, name FROM materials ORDER BY name", is_sqlite=is_sqlite)
        materials = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar materiales para el movimiento de stock: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_materials"))

    if request.method == "POST":
        material_id = request.form["material_id"]
        quantity = request.form.get("quantity", type=int)
        movement_type = request.form["movement_type"]
        notes = request.form.get("notes")

        if not all([material_id, quantity is not None, movement_type]):
            flash("Por favor, completa todos los campos obligatorios.", "danger")
            return render_template("stock_movements/form.html", title="Registrar Movimiento de Stock", materials=materials)

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO stock_movements (material_id, quantity, movement_type, notes) VALUES (?, ?, ?, ?)",
                (material_id, quantity, movement_type, notes),
                is_sqlite=is_sqlite
            )
            
            # Update material stock
            if movement_type == "entrada":
                _execute_sql(cursor, "UPDATE materials SET current_stock = current_stock + ? WHERE id = ?", (quantity, material_id), is_sqlite=is_sqlite)
            elif movement_type == "salida":
                _execute_sql(cursor, "UPDATE materials SET current_stock = current_stock - ? WHERE id = ?", (quantity, material_id), is_sqlite=is_sqlite)
            
            conn.commit()
            flash("Movimiento de stock registrado exitosamente.", "success")
            log_activity(current_user.id, "ADD_STOCK_MOVEMENT", f"Added stock movement for material ID: {material_id}, type: {movement_type}, quantity: {quantity}.")
            return redirect(url_for("list_materials"))
        except Exception as e:
            flash(f"Error al registrar movimiento de stock: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("stock_movements/form.html", title="Registrar Movimiento de Stock", materials=materials)


@app.route("/materials/edit/<int:material_id>", methods=["GET", "POST"])
@login_required
@permission_required("manage_materials")
def edit_material(material_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    material = None
    try:
        _execute_sql(cursor, "SELECT * FROM materials WHERE id = ?", (material_id,), is_sqlite=is_sqlite)
        material = cursor.fetchone()
        if not material:
            flash("Material no encontrado.", "danger")
            return redirect(url_for("list_materials"))
    except Exception as e:
        flash(f"Error al cargar material: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_materials"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description")
        current_stock = request.form.get("current_stock", type=int)
        unit_price = request.form.get("unit_price", type=float)
        min_stock_level = request.form.get("min_stock_level", type=int)
        unit_of_measure = request.form.get("unit_of_measure")

        if not all([name, current_stock is not None, unit_price is not None, min_stock_level is not None]):
            flash("Por favor, completa todos los campos obligatorios.", "danger")
            return render_template("materials/form.html", title="Editar Material", material=material)

        try:
            _execute_sql(cursor,
                "UPDATE materials SET name = ?, description = ?, current_stock = ?, unit_price = ?, min_stock_level = ?, unit_of_measure = ? WHERE id = ?",
                (name, description, current_stock, unit_price, min_stock_level, unit_of_measure, material_id),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Material actualizado exitosamente.", "success")
            log_activity(current_user.id, "EDIT_MATERIAL", f"Edited material: {name} (ID: {material_id}).")
            return redirect(url_for("list_materials"))
        except Exception as e:
            flash(f"Error al actualizar material: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("materials/form.html", title="Editar Material", material=material)


@app.route("/materials/delete/<int:material_id>", methods=["POST"])
@login_required
@permission_required("manage_materials")
def delete_material(material_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "DELETE FROM materials WHERE id = ?", (material_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Material eliminado exitosamente.", "success")
        log_activity(current_user.id, "DELETE_MATERIAL", f"Deleted material ID: {material_id}.")
    except Exception as e:
        flash(f"Error al eliminar material: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_materials"))


@app.route("/clients")
@login_required
@permission_required("view_clients")
def list_clients():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    clients = []
    try:
        _execute_sql(cursor, "SELECT * FROM clients ORDER BY nombre ASC", is_sqlite=is_sqlite)
        clients = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar clientes: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("clients/list.html", clients=clients)


@app.route("/clients/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_clients")
def add_client():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        nombre = request.form["nombre"]
        direccion = request.form.get("direccion")
        telefono = request.form.get("telefono")
        email = request.form.get("email")

        if not nombre:
            flash("Por favor, completa el campo de nombre.", "danger")
            return render_template("clients/form.html", title="Añadir Cliente")

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
                (nombre, direccion, telefono, email),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Cliente añadido exitosamente.", "success")
            log_activity(current_user.id, "ADD_CLIENT", f"Added client: {nombre}.")
            return redirect(url_for("list_clients"))
        except Exception as e:
            flash(f"Error al añadir cliente: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("clients/form.html", title="Añadir Cliente")


@app.route("/clients/edit/<int:client_id>", methods=["GET", "POST"])
@login_required
@permission_required("manage_clients")
def edit_client(client_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    client = None
    try:
        _execute_sql(cursor, "SELECT * FROM clients WHERE id = ?", (client_id,), is_sqlite=is_sqlite)
        client = cursor.fetchone()
        if not client:
            flash("Cliente no encontrado.", "danger")
            return redirect(url_for("list_clients"))
    except Exception as e:
        flash(f"Error al cargar cliente: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_clients"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        direccion = request.form.get("direccion")
        telefono = request.form.get("telefono")
        email = request.form.get("email")

        if not nombre:
            flash("Por favor, completa el campo de nombre.", "danger")
            return render_template("clients/form.html", title="Editar Cliente", client=client)

        try:
            _execute_sql(cursor,
                "UPDATE clients SET nombre = ?, direccion = ?, telefono = ?, email = ? WHERE id = ?",
                (nombre, direccion, telefono, email, client_id),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Cliente actualizado exitosamente.", "success")
            log_activity(current_user.id, "EDIT_CLIENT", f"Edited client: {nombre} (ID: {client_id}).")
            return redirect(url_for("list_clients"))
        except Exception as e:
            flash(f"Error al actualizar cliente: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("clients/form.html", title="Editar Cliente", client=client)


@app.route("/clients/delete/<int:client_id>", methods=["POST"])
@login_required
@permission_required("manage_clients")
def delete_client(client_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "DELETE FROM clients WHERE id = ?", (client_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Cliente eliminado exitosamente.", "success")
        log_activity(current_user.id, "DELETE_CLIENT", f"Deleted client ID: {client_id}.")
    except Exception as e:
        flash(f"Error al eliminar cliente: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_clients"))


@app.route("/services")
@login_required
@permission_required("view_services")
def list_services():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    services = []
    try:
        _execute_sql(cursor, "SELECT * FROM services ORDER BY name ASC", is_sqlite=is_sqlite)
        services = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar servicios: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("services/list.html", services=services)


@app.route("/services/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_services")
def add_service():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description")
        price = request.form.get("price", type=float)
        category = request.form.get("category")

        if not all([name, price is not None]):
            flash("Por favor, completa todos los campos obligatorios (Nombre y Precio).", "danger")
            return render_template("services/form.html", title="Añadir Servicio")

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO services (name, description, price, category) VALUES (?, ?, ?, ?)",
                (name, description, price, category),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Servicio añadido exitosamente.", "success")
            log_activity(current_user.id, "ADD_SERVICE", f"Added service: {name}.")
            return redirect(url_for("list_services"))
        except Exception as e:
            flash(f"Error al añadir servicio: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("services/form.html", title="Añadir Servicio")


@app.route("/services/edit/<int:service_id>", methods=["GET", "POST"])
@login_required
@permission_required("manage_services")
def edit_service(service_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    service = None
    try:
        _execute_sql(cursor, "SELECT * FROM services WHERE id = ?", (service_id,), is_sqlite=is_sqlite)
        service = cursor.fetchone()
        if not service:
            flash("Servicio no encontrado.", "danger")
            return redirect(url_for("list_services"))
    except Exception as e:
        flash(f"Error al cargar servicio: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_services"))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description")
        price = request.form.get("price", type=float)
        category = request.form.get("category")

        if not all([name, price is not None]):
            flash("Por favor, completa todos los campos obligatorios (Nombre y Precio).", "danger")
            return render_template("services/form.html", title="Editar Servicio", service=service)

        try:
            _execute_sql(cursor,
                "UPDATE services SET name = ?, description = ?, price = ?, category = ? WHERE id = ?",
                (name, description, price, category, service_id),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Servicio actualizado exitosamente.", "success")
            log_activity(current_user.id, "EDIT_SERVICE", f"Edited service: {name} (ID: {service_id}).")
            return redirect(url_for("list_services"))
        except Exception as e:
            flash(f"Error al actualizar servicio: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("services/form.html", title="Editar Servicio", service=service)


@app.route("/services/delete/<int:service_id>", methods=["POST"])
@login_required
@permission_required("manage_services")
def delete_service(service_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "DELETE FROM services WHERE id = ?", (service_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Servicio eliminado exitosamente.", "success")
        log_activity(current_user.id, "DELETE_SERVICE", f"Deleted service ID: {service_id}.")
    except Exception as e:
        flash(f"Error al eliminar servicio: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_services"))


@app.route("/proveedores")
@login_required
@permission_required("view_proveedores")
def list_proveedores():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    proveedores = []
    try:
        _execute_sql(cursor, "SELECT * FROM proveedores ORDER BY nombre ASC", is_sqlite=is_sqlite)
        proveedores = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar proveedores: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("proveedores/list.html", proveedores=proveedores)


@app.route("/proveedores/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_proveedores")
def add_proveedor():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        nombre = request.form["nombre"]
        contacto = request.form.get("contacto")
        telefono = request.form.get("telefono")
        email = request.form.get("email")
        direccion = request.form.get("direccion")
        tipo = request.form.get("tipo")

        if not all([nombre, tipo]):
            flash("Por favor, completa todos los campos obligatorios (Nombre y Tipo).", "danger")
            return render_template("proveedores/form.html", title="Añadir Proveedor")

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)",
                (nombre, contacto, telefono, email, direccion, tipo),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Proveedor añadido exitosamente.", "success")
            log_activity(current_user.id, "ADD_PROVEEDOR", f"Added provider: {nombre}.")
            return redirect(url_for("list_proveedores"))
        except Exception as e:
            flash(f"Error al añadir proveedor: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("proveedores/form.html", title="Añadir Proveedor")


@app.route("/proveedores/edit/<int:proveedor_id>", methods=["GET", "POST"])
@login_required
@permission_required("manage_proveedores")
def edit_proveedor(proveedor_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    proveedor = None
    try:
        _execute_sql(cursor, "SELECT * FROM proveedores WHERE id = ?", (proveedor_id,), is_sqlite=is_sqlite)
        proveedor = cursor.fetchone()
        if not proveedor:
            flash("Proveedor no encontrado.", "danger")
            return redirect(url_for("list_proveedores"))
    except Exception as e:
        flash(f"Error al cargar proveedor: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_proveedores"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        contacto = request.form.get("contacto")
        telefono = request.form.get("telefono")
        email = request.form.get("email")
        direccion = request.form.get("direccion")
        tipo = request.form.get("tipo")

        if not all([nombre, tipo]):
            flash("Por favor, completa todos los campos obligatorios (Nombre y Tipo).", "danger")
            return render_template("proveedores/form.html", title="Editar Proveedor", proveedor=proveedor)

        try:
            _execute_sql(cursor,
                "UPDATE proveedores SET nombre = ?, contacto = ?, telefono = ?, email = ?, direccion = ?, tipo = ? WHERE id = ?",
                (nombre, contacto, telefono, email, direccion, tipo, proveedor_id),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Proveedor actualizado exitosamente.", "success")
            log_activity(current_user.id, "EDIT_PROVEEDOR", f"Edited provider: {nombre} (ID: {proveedor_id}).")
            return redirect(url_for("list_proveedores"))
        except Exception as e:
            flash(f"Error al actualizar proveedor: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("proveedores/form.html", title="Editar Proveedor", proveedor=proveedor)


@app.route("/proveedores/delete/<int:proveedor_id>", methods=["POST"])
@login_required
@permission_required("manage_proveedores")
def delete_proveedor(proveedor_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "DELETE FROM proveedores WHERE id = ?", (proveedor_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Proveedor eliminado exitosamente.", "success")
        log_activity(current_user.id, "DELETE_PROVEEDOR", f"Deleted provider ID: {proveedor_id}.")
    except Exception as e:
        flash(f"Error al eliminar proveedor: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_proveedores"))


@app.route("/freelancers")
@login_required
@permission_required("view_freelancers")
def list_freelancers():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    freelancers = []
    try:
        _execute_sql(cursor, "SELECT u.id, u.username, fd.category, fd.specialty FROM users u JOIN freelancer_details fd ON u.id = fd.id ORDER BY u.username ASC", is_sqlite=is_sqlite)
        freelancers = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar autónomos: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("freelancers/list.html", freelancers=freelancers)


@app.route("/reports/financial")
@login_required
@permission_required("view_financial_reports")
def financial_reports():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    total_presupuesto = 0.0
    total_costo_materiales = 0.0
    total_costo_mano_obra = 0.0
    total_gastos = 0.0
    total_beneficio_bruto = 0.0
    total_iva_ingresos = 0.0
    total_iva_gastos = 0.0
    total_iva_neto = 0.0
    trabajos_data = []

    try:
        # Calculate total_presupuesto (from all jobs, not just finished)
        _execute_sql(cursor, "SELECT SUM(presupuesto) FROM trabajos", is_sqlite=is_sqlite)
        res = cursor.fetchone()
        if res and res[0] is not None:
            total_presupuesto = res[0]

        # Calculate total_costo_materiales (from stock movements or direct material costs in tasks/jobs)
        # For simplicity, let's assume material costs are linked to tasks for now
        _execute_sql(cursor, "SELECT SUM(monto_abonado) FROM tareas WHERE metodo_pago IS NOT NULL AND estado_pago = 'Abonado'", is_sqlite=is_sqlite)
        res = cursor.fetchone()
        if res and res[0] is not None:
            total_costo_materiales = res[0] # Re-using monto_abonado from tasks for material costs

        # Calculate total_costo_mano_obra (from freelancer payments or estimated labor costs)
        # This is a placeholder, actual implementation depends on how labor costs are tracked
        total_costo_mano_obra = 0.0 # Placeholder for now

        total_gastos = total_costo_materiales + total_costo_mano_obra

        total_beneficio_bruto = total_presupuesto - total_gastos

        # Calculate IVA (assuming VAT rate is stored with jobs)
        # This is a simplified calculation, actual IVA calculation can be complex
        _execute_sql(cursor, "SELECT SUM(presupuesto * (vat_rate / 100.0)) FROM trabajos WHERE vat_rate IS NOT NULL", is_sqlite=is_sqlite)
        res = cursor.fetchone()
        if res and res[0] is not None:
            total_iva_ingresos = res[0]

        # Assuming a fixed IVA rate for expenses or it's included in monto
        total_iva_gastos = total_gastos * 0.21 # Assuming 21% IVA on expenses for simplicity

        total_iva_neto = total_iva_ingresos - total_iva_gastos

        # Fetch detailed job data for the table
        _execute_sql(cursor, """
            SELECT 
                t.id, 
                t.titulo, 
                c.nombre as client_nombre, 
                t.presupuesto,
                COALESCE(SUM(CASE WHEN ta.metodo_pago IS NOT NULL AND ta.estado_pago = 'Abonado' THEN ta.monto_abonado ELSE 0 END), 0) as costo_total_materiales,
                0.0 as costo_total_mano_obra -- Placeholder for now
            FROM trabajos t
            JOIN clients c ON t.client_id = c.id
            LEFT JOIN tareas ta ON t.id = ta.trabajo_id
            GROUP BY t.id, t.titulo, c.nombre, t.presupuesto
            ORDER BY t.fecha_visita DESC
        """, is_sqlite=is_sqlite)
        trabajos_data = cursor.fetchall()

    except Exception as e:
        flash(f"Error al cargar informes financieros: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template("reports/financial.html", 
                           total_presupuesto=total_presupuesto,
                           total_costo_materiales=total_costo_materiales,
                           total_costo_mano_obra=total_costo_mano_obra,
                           total_gastos=total_gastos,
                           total_beneficio_bruto=total_beneficio_bruto,
                           total_iva_ingresos=total_iva_ingresos,
                           total_iva_gastos=total_iva_gastos,
                           total_iva_neto=total_iva_neto,
                           trabajos=trabajos_data)


@app.route("/trabajos/approval")
@login_required
@permission_required("manage_all_jobs")
def job_approval_list():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    jobs_for_approval = []
    try:
        # Assuming there's a status like 'Pendiente de Aprobacion' or similar
        _execute_sql(cursor, "SELECT t.id, t.titulo, t.descripcion, t.estado, c.nombre as client_name, u.username as autonomo_name FROM trabajos t JOIN clients c ON t.client_id = c.id LEFT JOIN users u ON t.autonomo_id = u.id WHERE t.estado = 'Pendiente de Aprobacion' ORDER BY t.fecha_visita DESC", is_sqlite=is_sqlite)
        jobs_for_approval = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar trabajos para aprobación: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("trabajos/approval.html", jobs_for_approval=jobs_for_approval)


@app.route("/trabajos/approve/<int:trabajo_id>", methods=["POST"])
@login_required
@permission_required("manage_all_jobs")
def approve_job(trabajo_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "UPDATE trabajos SET estado = 'Aprobado' WHERE id = ?", (trabajo_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Trabajo aprobado exitosamente.", "success")
        log_activity(current_user.id, "APPROVE_JOB", f"Approved job ID: {trabajo_id}.")
    except Exception as e:
        flash(f"Error al aprobar trabajo: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("job_approval_list"))


@app.route("/trabajos/reject/<int:trabajo_id>")
@login_required
@permission_required("manage_all_jobs")
def reject_job(trabajo_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "UPDATE trabajos SET estado = 'Rechazado' WHERE id = ?", (trabajo_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Trabajo rechazado exitosamente.", "success")
        log_activity(current_user.id, "REJECT_JOB", f"Rejected job ID: {trabajo_id}.")
    except Exception as e:
        flash(f"Error al rechazar trabajo: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("job_approval_list"))


@app.route("/trabajos/complete/<int:trabajo_id>", methods=["POST"])
@login_required
@permission_required("manage_all_jobs") # Or manage_own_jobs
def complete_job(trabajo_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "UPDATE trabajos SET estado = 'Finalizado' WHERE id = ?", (trabajo_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Trabajo marcado como finalizado exitosamente.", "success")
        log_activity(current_user.id, "COMPLETE_JOB", f"Completed job ID: {trabajo_id}.")
    except Exception as e:
        flash(f"Error al finalizar trabajo: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_trabajos"))


@app.route("/trabajos/delete/<int:trabajo_id>", methods=["POST"])
@login_required
@permission_required("manage_all_jobs")
def delete_trabajo(trabajo_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "DELETE FROM trabajos WHERE id = ?", (trabajo_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Trabajo eliminado exitosamente.", "success")
        log_activity(current_user.id, "DELETE_JOB", f"Deleted job ID: {trabajo_id}.")
    except Exception as e:
        flash(f"Error al eliminar trabajo: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_trabajos"))


@app.route("/gastos/add/<int:trabajo_id>", methods=["GET", "POST"])
@login_required
@permission_required("manage_all_jobs") # Or manage_own_jobs
def add_gasto(trabajo_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    trabajo = None
    try:
        cursor = conn.cursor()
        _execute_sql(cursor, "SELECT id, titulo FROM trabajos WHERE id = ?", (trabajo_id,), is_sqlite=is_sqlite)
        trabajo = cursor.fetchone()
        if not trabajo:
            flash("Trabajo no encontrado.", "danger")
            return redirect(url_for("list_trabajos"))
    except Exception as e:
        flash(f"Error al cargar trabajo: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_trabajos"))

    if request.method == "POST":
        descripcion = request.form["descripcion"]
        tipo = request.form["tipo"]
        monto = request.form.get("monto", type=float)
        fecha = request.form.get("fecha")

        if not all([descripcion, tipo, monto is not None, fecha]):
            flash("Por favor, completa todos los campos obligatorios.", "danger")
            return render_template("gastos/form.html", title="Añadir Gasto", trabajo=trabajo)

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, fecha) VALUES (?, ?, ?, ?, ?)",
                (trabajo_id, descripcion, tipo, monto, fecha),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Gasto añadido exitosamente.", "success")
            log_activity(current_user.id, "ADD_GASTO", f"Added expense for job ID: {trabajo_id}.")
            return redirect(url_for("edit_trabajo", trabajo_id=trabajo_id)) # Redirect back to job edit page
        except Exception as e:
            flash(f"Error al añadir gasto: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("gastos/form.html", title="Añadir Gasto", trabajo=trabajo)


@app.route("/users")
@login_required
@permission_required("view_users")
def list_users():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    users = []
    try:
        _execute_sql(cursor, "SELECT u.id, u.username, u.email, GROUP_CONCAT(r.name) as roles FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id GROUP BY u.id ORDER BY u.username ASC", is_sqlite=is_sqlite)
        users = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar usuarios: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("users/list.html", users=users)



@app.route("/users/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def add_user():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    
    roles = []
    try:
        cursor = conn.cursor()
        _execute_sql(cursor, "SELECT id, name FROM roles ORDER BY name", is_sqlite=is_sqlite)
        roles = cursor.fetchall()
    except Exception as e:
        flash(f"Error al cargar roles: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_users"))

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role_id = request.form["role_id"]
        is_active = 'is_active' in request.form

        hashed_password = generate_password_hash(password)

        try:
            cursor = conn.cursor()
            _execute_sql(cursor,
                "INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, ?) RETURNING id",
                (username, hashed_password, email, is_active),
                is_sqlite=is_sqlite
            )
            user_id = cursor.fetchone()[0]
            _execute_sql(cursor,
                "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, role_id),
                is_sqlite=is_sqlite
            )
            conn.commit()
            flash("Usuario añadido exitosamente.", "success")
            log_activity(current_user.id, "ADD_USER", f"Added user: {username} with role {role_id}.")
            return redirect(url_for("list_users"))
        except Exception as e:
            flash(f"Error al añadir usuario: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("users/form.html", title="Añadir Usuario", roles=roles)


@app.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def edit_user(user_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    user = None
    roles = []
    try:
        _execute_sql(cursor, "SELECT id, name FROM roles ORDER BY name", is_sqlite=is_sqlite)
        roles = cursor.fetchall()
        _execute_sql(cursor, "SELECT u.id, u.username, u.email, u.is_active, ur.role_id FROM users u JOIN user_roles ur ON u.id = ur.user_id WHERE u.id = ?", (user_id,), is_sqlite=is_sqlite)
        user = cursor.fetchone()
        if not user:
            flash("Usuario no encontrado.", "danger")
            return redirect(url_for("list_users"))
    except Exception as e:
        flash(f"Error al cargar datos del usuario: {e}", "danger")
        if conn: conn.close()
        return redirect(url_for("list_users"))

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form.get("password")
        role_id = request.form["role_id"]
        is_active = 'is_active' in request.form

        try:
            # Update user details
            if password:
                hashed_password = generate_password_hash(password)
                _execute_sql(cursor,
                    "UPDATE users SET username = ?, email = ?, password_hash = ?, is_active = ? WHERE id = ?",
                    (username, email, hashed_password, is_active, user_id),
                    is_sqlite=is_sqlite
                )
            else:
                _execute_sql(cursor,
                    "UPDATE users SET username = ?, email = ?, is_active = ? WHERE id = ?",
                    (username, email, is_active, user_id),
                    is_sqlite=is_sqlite
                )
            
            # Update user role
            _execute_sql(cursor, "UPDATE user_roles SET role_id = ? WHERE user_id = ?", (role_id, user_id), is_sqlite=is_sqlite)
            
            conn.commit()
            flash("Usuario actualizado exitosamente.", "success")
            log_activity(current_user.id, "EDIT_USER", f"Edited user: {username} (ID: {user_id}).")
            return redirect(url_for("list_users"))
        except Exception as e:
            flash(f"Error al actualizar usuario: {e}", "danger")
            conn.rollback()
        finally:
            if conn: conn.close()

    return render_template("users/form.html", title="Editar Usuario", user=user, roles=roles)


@app.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@permission_required("manage_users")
def delete_user(user_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "DELETE FROM users WHERE id = ?", (user_id,), is_sqlite=is_sqlite)
        _execute_sql(cursor, "DELETE FROM user_roles WHERE user_id = ?", (user_id,), is_sqlite=is_sqlite)
        conn.commit()
        flash("Usuario eliminado exitosamente.", "success")
        log_activity(current_user.id, "DELETE_USER", f"Deleted user ID: {user_id}.")
    except Exception as e:
        flash(f"Error al eliminar usuario: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_users"))


@app.route("/notifications")
@login_required
@permission_required("manage_notifications")
def list_notifications():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    notifications = []
    try:
        _execute_sql(cursor, "SELECT * FROM notifications WHERE user_id = ? ORDER BY timestamp DESC", (current_user.id,), is_sqlite=is_sqlite)
        notifications = cursor.fetchall()
        # Mark notifications as read
        _execute_sql(cursor, "UPDATE notifications SET is_read = TRUE WHERE user_id = ?", (current_user.id,), is_sqlite=is_sqlite)
        conn.commit()
    except Exception as e:
        flash(f"Error al cargar notificaciones: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return render_template("notifications/list.html", notifications=notifications)


@app.route("/api/unread_notifications_count")
@login_required
def unread_notifications_count():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        return jsonify({"count": 0}) # Return 0 if no DB connection
    cursor = conn.cursor()
    count = 0
    try:
        _execute_sql(cursor, "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = FALSE", (current_user.id,), is_sqlite=is_sqlite)
        result = cursor.fetchone()
        if result:
            count = result[0]
    except Exception as e:
        print(f"Error fetching unread notification count: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return jsonify({"count": count})


@app.route("/notifications/mark_read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    try:
        _execute_sql(cursor, "UPDATE notifications SET is_read = TRUE WHERE id = ? AND user_id = ?", (notification_id, current_user.id), is_sqlite=is_sqlite)
        conn.commit()
        flash("Notificación marcada como leída.", "success")
    except Exception as e:
        flash(f"Error al marcar notificación como leída: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_notifications"))


@app.route("/notifications/snooze/<int:notification_id>", methods=["POST"])
@login_required
def snooze_notification(notification_id):
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    
    duration = request.form.get("duration")
    snooze_until = datetime.now()

    if duration == "1_day":
        snooze_until += timedelta(days=1)
    elif duration == "3_days":
        snooze_until += timedelta(days=3)
    elif duration == "1_week":
        snooze_until += timedelta(weeks=1)
    elif duration == "tomorrow":
        snooze_until = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    try:
        _execute_sql(cursor, "UPDATE notifications SET snooze_until = ?, is_read = FALSE WHERE id = ? AND user_id = ?", (snooze_until.isoformat(), notification_id, current_user.id), is_sqlite=is_sqlite)
        conn.commit()
        flash("Notificación pospuesta exitosamente.", "success")
    except Exception as e:
        flash(f"Error al posponer notificación: {e}", "danger")
        conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect(url_for("list_notifications"))


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/register/client", methods=["GET", "POST"])
def register_client():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return render_template("register_client.html")

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        full_name = request.form.get("full_name")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")
        dni = request.form.get("dni")

        hashed_password = generate_password_hash(password)

        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, is_active, full_name, phone_number, address, dni) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (username, hashed_password, email, True, full_name, phone_number, address, dni),
            )
            user_id = cursor.fetchone()[0]

            # Assign 'Cliente' role
            cursor.execute("SELECT id FROM roles WHERE name = %s", ("Cliente",))
            client_role_id = cursor.fetchone()["id"]
            cursor.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                (user_id, client_role_id),
            )

            conn.commit()
            flash(
                f'Usuario "{username}" registrado exitosamente como Cliente. Ahora puedes iniciar sesión.',
                "success",
            )
            log_activity(user_id, "REGISTER_CLIENT", f"New client registered: {username}.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Error: El nombre de usuario o el email ya existen.", "danger")
            conn.rollback()
        finally:
            if 'cursor' in locals() and cursor is not None: cursor.close()
            if conn is not None: conn.close()

    return render_template("register_client.html")

@app.route("/register/freelancer", methods=["GET", "POST"])
def register_freelancer():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return render_template("register_freelancer.html")

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        full_name = request.form.get("full_name")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")
        dni = request.form.get("dni")

        # Freelancer specific fields
        category = request.form.get("category", "")
        specialty = request.form.get("specialty", "")
        city_province = request.form.get("city_province", "")
        web = request.form.get("web", "")
        notes = request.form.get("notes", "")
        source_url = request.form.get("source_url", "")
        hourly_rate_normal = float(request.form.get("hourly_rate_normal", 0.0))
        hourly_rate_tier2 = float(request.form.get("hourly_rate_tier2", 0.0))
        hourly_rate_tier3 = float(request.form.get("hourly_rate_tier3", 0.0))
        difficulty_surcharge_rate = float(request.form.get("difficulty_surcharge_rate", 0.0))

        hashed_password = generate_password_hash(password)

        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, is_active, full_name, phone_number, address, dni) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (username, hashed_password, email, True, full_name, phone_number, address, dni),
            )
            user_id = cursor.fetchone()[0]

            # Assign 'Autonomo' role
            cursor.execute("SELECT id FROM roles WHERE name = %s", ("Autonomo",))
            autonomo_role_id = cursor.fetchone()["id"]
            cursor.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                (user_id, autonomo_role_id),
            )

            # Insert into freelancer_details
            cursor.execute(
                "INSERT INTO freelancer_details (id, category, specialty, city_province, address, web, phone, whatsapp, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    user_id, category, specialty, city_province, address, web, phone_number, phone_number, notes, source_url,
                    hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate
                ),
            )

            # Handle file uploads
            if 'project_files' in request.files:
                files = request.files.getlist('project_files')
                for file in files:
                    if file and file.filename != '':
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        # Store file path in the new uploaded_files table
                        cursor.execute(
                            "INSERT INTO uploaded_files (user_id, file_path) VALUES (%s, %s)",
                            (user_id, file_path)
                        )

            conn.commit()
            flash(
                f'Usuario "{username}" registrado exitosamente como Autónomo. Ahora puedes iniciar sesión.',
                "success",
            )
            log_activity(user_id, "REGISTER_FREELANCER", f"New freelancer registered: {username}.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Error: El nombre de usuario o el email ya existen.", "danger")
            conn.rollback()
        finally:
            if 'cursor' in locals() and cursor is not None: cursor.close()
            if conn is not None: conn.close()

    return render_template("register_freelancer.html")

@app.route("/register/provider", methods=["GET", "POST"])
def register_provider():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return render_template("register_provider.html")

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        full_name = request.form.get("full_name")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")
        dni = request.form.get("dni")

        # Provider specific fields
        company_name = request.form.get("company_name", "")
        contact_person = request.form.get("contact_person", "")
        provider_phone = request.form.get("provider_phone", "")
        provider_email = request.form.get("provider_email", "")
        provider_address = request.form.get("provider_address", "")
        service_type = request.form.get("service_type", "")
        web = request.form.get("web", "")
        notes = request.form.get("notes", "")

        hashed_password = generate_password_hash(password)

        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, is_active, full_name, phone_number, address, dni) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (username, hashed_password, email, True, full_name, phone_number, address, dni),
            )
            user_id = cursor.fetchone()[0]

            # Assign 'Proveedor' role
            cursor.execute("SELECT id FROM roles WHERE name = %s", ("Proveedor",))
            provider_role_id = cursor.fetchone()["id"]
            cursor.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                (user_id, provider_role_id),
            )

            # Insert into provider_details
            cursor.execute(
                "INSERT INTO provider_details (id, company_name, contact_person, phone, email, address, service_type, web, notes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    user_id, company_name, contact_person, provider_phone, provider_email, provider_address, service_type, web, notes
                ),
            )

            # Handle file uploads
            if 'project_files' in request.files:
                files = request.files.getlist('project_files')
                for file in files:
                    if file and file.filename != '':
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        
                        # Store file path in the new uploaded_files table
                        cursor.execute(
                            "INSERT INTO uploaded_files (user_id, file_path) VALUES (%s, %s)",
                            (user_id, file_path)
                        )

            conn.commit()
            flash(
                f'Usuario "{username}" registrado exitosamente como Proveedor. Ahora puedes iniciar sesión.',
                "success",
            )
            log_activity(user_id, "REGISTER_PROVIDER", f"New provider registered: {username}.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Error: El nombre de usuario o el email ya existen.", "danger")
            conn.rollback()
        finally:
            if 'cursor' in locals() and cursor is not None: cursor.close()
            if conn is not None: conn.close()

    return render_template("register_provider.html")

@app.route("/profile")
@login_required
def user_profile():
    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    if is_sqlite:
        cursor.execute(
            "SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = ?",
            (current_user.id,),
        )
    else:
        cursor.execute(
            "SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = %s",
            (current_user.id,),
        )
    user_roles = cursor.fetchall()
    roles = [row["name"] for row in user_roles]
    cursor.close()
    conn.close()
    return render_template("users/profile.html", user=current_user, roles=roles)


@app.route('/uploads/<filename>')
@login_required
@permission_required('upload_files')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/user/<int:user_id>/files')
@login_required
@permission_required('manage_users')
def user_files(user_id):
    

    conn, is_sqlite = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for('dashboard'))
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM uploaded_files WHERE user_id = %s", (user_id,))
    files = cursor.fetchall()
    
    cursor.execute("SELECT username FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user is None:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('dashboard'))

    return render_template("users/user_files.html", files=files, user=user)
