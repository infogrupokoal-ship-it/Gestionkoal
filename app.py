import sqlite3
import click
import csv  # New import
import os  # New import
import re  # New import
import urllib.parse  # New import
import psycopg2  # New import
import psycopg2.extras  # New import
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
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
                    except psycopg2.Error as e:
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
        cursor.execute("SELECT id FROM roles WHERE name = 'Admin'")
        admin_role_id = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM roles WHERE name = 'Oficinista'")
        oficinista_role_id = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM roles WHERE name = 'Autonomo'")
        autonomo_role_id = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM roles WHERE name = 'Cliente'")
        cliente_role_id = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM roles WHERE name = 'Proveedor'")
        proveedor_role_id = cursor.fetchone()["id"]
    else:
        cursor.execute("SELECT id FROM roles WHERE name = %s", ("Admin",))
        admin_role_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM roles WHERE name = %s", ("Oficinista",))
        oficinista_role_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM roles WHERE name = %s", ("Autonomo",))
        autonomo_role_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM roles WHERE name = %s", ("Cliente",))
        cliente_role_id = cursor.fetchone()[0]

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


# --- Database Connection ---
def get_db_connection():
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        # Connect to PostgreSQL
        print("Attempting to connect to PostgreSQL...")  # Debug print
        try:
            # Parse the DATABASE_URL to extract components
            result = urllib.parse.urlparse(DATABASE_URL)
            username = result.username
            password = result.password
            database = result.path[1:].strip()  # Remove leading '/' and trim whitespace
            hostname = result.hostname
            port = result.port

            # Construct connection string with trimmed database name
            conn = psycopg2.connect(
                host=hostname,
                port=port,
                database=database,
                user=username,
                password=password,
            )
            conn.autocommit = False  # Manage transactions manually

            conn.cursor_factory = psycopg2.extras.DictCursor

            # Check if tables exist, if not, initialize
            cursor = conn.cursor()
            cursor.execute(
                "SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'users');"
            )
            tables_exist = cursor.fetchone()[0]
            cursor.close()

            if not tables_exist:
                print(
                    "PostgreSQL tables not found. Initializing new PostgreSQL database..."
                )
                with current_app.app_context():  # Use current_app
                    setup_new_database(conn, is_sqlite=False)
                print("PostgreSQL database initialized.")

            print("Successfully connected to PostgreSQL.")  # Debug print
            return conn
        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL: {e}")  # Debug print
            import traceback

            traceback.print_exc()  # Print full traceback
            print(
                "Falling back to SQLite for local development (PostgreSQL connection failed)."
            )  # Debug print
            try:  # Added try-except for SQLite connection
                db_path = "database.db"
                db_is_new = not os.path.exists(db_path)
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA foreign_keys = ON")
                conn.row_factory = sqlite3.Row
                if db_is_new:
                    print(
                        "SQLite database not found. Initializing new SQLite database..."
                    )
                    with current_app.app_context():  # Use current_app
                        setup_new_database(conn, is_sqlite=True)
                    print("SQLite database initialized.")
                return conn
            except sqlite3.Error as sqlite_e:  # Catch SQLite errors
                print(f"Error connecting to SQLite fallback: {sqlite_e}")
                import traceback

                traceback.print_exc()  # Print full traceback
                return None  # Explicitly return None if SQLite fallback fails
    else:
        print(
            "DATABASE_URL not set. Connecting to SQLite for local development."
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
            return conn
        except sqlite3.Error as sqlite_e:  # Catch SQLite errors
            print(f"Error connecting to SQLite: {sqlite_e}")
            import traceback

            traceback.print_exc()  # Print full traceback
            return None  # Explicitly return None if SQLite fails


# --- Activity Logging Function ---
def log_activity(user_id, action, details=None):
    conn = get_db_connection()
    if conn is None:
        print("Error: Could not connect to database for activity logging.")
        return
    cursor = conn.cursor()  # Get a cursor
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO activity_log (user_id, action, details, timestamp) VALUES (%s, %s, %s, %s)",
        (user_id, action, details, timestamp),
    )  # Use cursor.execute and %s
    conn.commit()
    cursor.close()  # Close cursor
    conn.close()  # Close connection


# --- Notification Generation Function ---
def generate_notifications_for_user(user_id):
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # 1. Upcoming Jobs
        cursor.execute(
            "SELECT id, titulo, fecha_visita FROM trabajos WHERE fecha_visita::date BETWEEN date(%s) AND date(%s, '+7 days') AND estado != 'Finalizado'",
            (today, today),
        )
        upcoming_jobs = cursor.fetchall()
        for job in upcoming_jobs:
            message = f"El trabajo '{job['titulo']}' está programado para el {job['fecha_visita']}."
            cursor.execute(
                "SELECT id FROM notifications WHERE user_id = %s AND type = 'job_reminder' AND related_id = %s AND message = %s",
                (user_id, job["id"], message),
            )
            if not cursor.fetchone():
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
        cursor.execute(
            "SELECT t.id, t.titulo, t.fecha_limite, tr.titulo as trabajo_titulo FROM tareas t "
            "JOIN trabajos tr ON t.trabajo_id = tr.id "
            "WHERE t.fecha_limite < %s AND t.estado != 'Completada' AND t.autonomo_id = %s",
            (today, user_id),
        )
        overdue_tasks = cursor.fetchall()
        for task in overdue_tasks:
            message = f"La tarea '{task['titulo']}' del trabajo '{task['trabajo_titulo']}' está atrasada desde el {task['fecha_limite']}."
            cursor.execute(
                "SELECT id FROM notifications WHERE user_id = %s AND type = 'task_overdue' AND related_id = %s AND message = %s",
                (user_id, task["id"], message),
            )
            if not cursor.fetchone():
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
        cursor.execute(
            "SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = %s",
            (user_id,),
        )
        user_roles = cursor.fetchall()
        role_names = [role["name"] for role in user_roles]

        if "Admin" in role_names or "Oficinista" in role_names:
            cursor.execute(
                "SELECT id, name, current_stock, min_stock_level FROM materials WHERE current_stock <= min_stock_level"
            )
            low_stock_materials = cursor.fetchall()
            for material in low_stock_materials:
                message = f"El material '{material['name']}' tiene bajo stock: {material['current_stock']} (Mínimo: {material['min_stock_level']})."
                cursor.execute(
                    "SELECT id FROM notifications WHERE user_id = %s AND type = 'low_stock' AND related_id = %s AND message = %s",
                    (user_id, material["id"], message),
                )
                if not cursor.fetchone():
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
    except (psycopg2.Error, sqlite3.Error) as e:
        print(f"Error generating notifications: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


# --- Database Initialization Command ---
@click.command("init-db")
def init_db_command():
    """Clear the existing data and create new tables with a large set of sample data."""
    db = get_db_connection()
    if db is None:
        click.echo("Error: Could not connect to database for init-db command.")
        return
    try:
        is_sqlite_conn = isinstance(db, sqlite3.Connection)
        with current_app.app_context():
            setup_new_database(db, is_sqlite=is_sqlite_conn)
    except Exception as e:
        click.echo(f"Error during database setup: {e}")
        db.rollback()
        return
    finally:
        if db:
            db.close()
        if 'cursor' in locals() and cursor is not None: cursor.close()

    db = get_db_connection()  # Reopen connection for data insertion
    if db is None:
        click.echo("Error: Could not reconnect to database after schema setup.")
        return
    cursor = db.cursor() # Define cursor here

    # Helper function to execute SQL with correct parameter style
    def _execute_sql(cursor, sql, params=None):
        if params is None:
            params = []
        if isinstance(db, sqlite3.Connection): # Check db type here
            cursor.execute(sql, params)
        else:
            # For psycopg2, use %s placeholders
            formatted_sql = sql.replace('?', '%s')
            cursor.execute(formatted_sql, params)

    # --- Roles ---
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Admin')")
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Oficinista')")
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Autonomo')")
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Cliente')")
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Proveedor')")
    db.commit()
    cursor.execute("SELECT id FROM roles WHERE name = 'Admin'")
    admin_role_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM roles WHERE name = 'Oficinista'")
    oficinista_role_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM roles WHERE name = 'Autonomo'")
    autonomo_role_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM roles WHERE name = 'Cliente'")
    cliente_role_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM roles WHERE name = 'Proveedor'")
    proveedor_role_id = cursor.fetchone()["id"]

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
    ]
    for perm_name in permissions_to_add:
        db.execute("INSERT OR IGNORE INTO permissions (name) VALUES (?)", (perm_name,))
    db.commit()

    # Assign permissions to roles
    def assign_permission(role_id, perm_name):
        cursor.execute("SELECT id FROM permissions WHERE name = ?", (perm_name,))
        perm_id = cursor.fetchone()["id"]
        cursor.execute(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            (role_id, perm_id),
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
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, ?)",
            (username, hashed_password, email, True),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id),
        )
    db.commit()
    cursor.execute("SELECT id FROM users WHERE username = 'Carlos Gomez'")
    carlos_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM users WHERE username = 'Sofia Lopez'")
    sofia_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM users WHERE username = 'Ana Torres'")
    ana_id = cursor.fetchone()["id"]

    # --- Clients ---
    db.execute(
        "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
        (
            "Constructora XYZ",
            "Calle Falsa 123, Valencia",
            "960123456",
            "contacto@constructoraxyz.com",
        ),
    )
    db.execute(
        "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
        (
            "Reformas El Sol",
            "Avenida del Puerto 50, Valencia",
            "960987654",
            "info@reformaselsol.es",
        ),
    )
    db.execute(
        "INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)",
        (
            "Comunidad de Vecinos El Roble",
            "Plaza del Arbol 1, Silla",
            "961231234",
            "admin@roble.com",
        ),
    )
    db.commit()
    cursor.execute("SELECT id FROM clients WHERE nombre = 'Constructora XYZ'")
    client1_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM clients WHERE nombre = 'Reformas El Sol'")
    client2_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM clients WHERE nombre = 'Comunidad de Vecinos El Roble'")
    client3_id = cursor.fetchone()["id"]

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
        db.execute(
            "INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, contacto, telefono, email, direccion, tipo),
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
        db.execute(
            "INSERT INTO materials (name, description, current_stock, unit_price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?, ?)",
            (name, desc, stock, price, recommended_price, last_sold_price),
        )

    db.execute(
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Instalación Eléctrica', 'Punto de luz completo', 50.00, 55.00, 48.00)"
    )
    db.execute(
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Fontanería', 'Instalación de grifo', 40.00, 45.00, 38.00)"
    )
    db.execute(
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Ejem_Servicio de Pintura', 'Pintura de pared interior', 30.00, 35.00, 28.00)"
    )
    db.execute(
        "INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Ejem_Servicio de Albañilería', 'Reparación de muro', 70.00, 75.00, 68.00)"
    )

    # --- Trabajos (Jobs) ---
    # --- Trabajos (Jobs) ---
    from datetime import date, timedelta
    import random

    today = date.today()

    # Insert a specific example job first to get its ID
    cursor.execute(
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
        ),
    )
    ejem_job_id = cursor.lastrowid

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
        db.execute(
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
            ),
        )

    # --- Tareas (Tasks) ---
    # Get an existing job_id to link tasks to
    ejem_autonomo_id = db.execute(
        "SELECT id FROM users WHERE username = 'Carlos Gomez'"
    ).fetchone()["id"]

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
            "Ejem_Instalar nuevo enchufe",
            "Instalación de enchufe doble en salón.",
            "Pendiente",
            (today + timedelta(days=7)).isoformat(),
            ejem_autonomo_id,
            "Pendiente",
            "Pendiente",
            0.00,
            None,
        ),
        (
            ejem_job_id,
            "Ejem_Comprar materiales",
            "Adquirir materiales para la reparación.",
            "Completada",
            (today - timedelta(days=2)).isoformat(),
            ejem_autonomo_id,
            "Efectivo",
            "Abonado",
            25.50,
            (today - timedelta(days=2)).isoformat(),
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
        db.execute(
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
            ),
        )

    # --- Job Material Installation Costs (Ejem) ---
    # Get existing material and service IDs
    ejem_material_id = db.execute(
        "SELECT id FROM materials WHERE name = 'Tornillos 5mm'"
    ).fetchone()["id"]
    ejem_service_id = db.execute(
        "SELECT id FROM services WHERE name = 'Instalación Eléctrica'"
    ).fetchone()["id"]

    job_install_costs_to_add = [
        (
            ejem_job_id,
            ejem_material_id,
            None,
            "Ejem_Costo de instalación de tornillos",
            5.00,
            10.00,
            (today + timedelta(days=1)).isoformat(),
            "Notas de instalación de tornillos.",
        ),
        (
            ejem_job_id,
            None,
            ejem_service_id,
            "Ejem_Costo de configuración eléctrica",
            20.00,
            30.00,
            (today + timedelta(days=2)).isoformat(),
            "Notas de configuración eléctrica.",
        ),
    ]
    for (
        job_id,
        material_id,
        service_id,
        description,
        cost,
        revenue,
        date,
        notes,
    ) in job_install_costs_to_add:
        db.execute(
            "INSERT INTO job_material_install_costs (job_id, material_id, service_id, description, cost, revenue, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, material_id, service_id, description, cost, revenue, date, notes),
        )

    # --- Gastos (Expenses) and Shared Expenses (Ejem) ---
    # Get existing job_id and freelancer IDs
    ejem_job_id_gasto = ejem_job_id  # Use the same example job ID
    carlos_id = db.execute(
        "SELECT id FROM users WHERE username = 'Carlos Gomez'"
    ).fetchone()["id"]
    sofia_id = db.execute(
        "SELECT id FROM users WHERE username = 'Sofia Lopez'"
    ).fetchone()["id"]

    # Example shared expense: a tool rental
    db.execute(
        "INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)",
        (
            ejem_job_id_gasto,
            "Ejem_Alquiler de furgoneta para transporte de material",
            "Transporte",
            120.00,
            21.0,
            (today - timedelta(days=5)).isoformat(),
        ),
    )
    gasto_furgoneta_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Carlos pays 70%
    db.execute(
        "INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)",
        (
            gasto_furgoneta_id,
            carlos_id,
            84.00,
            1,
            "Ejem_Carlos cubre la mayor parte del alquiler.",
        ),
    )
    # Sofia pays 30%
    db.execute(
        "INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)",
        (
            gasto_furgoneta_id,
            sofia_id,
            36.00,
            1,
            "Ejem_Sofía cubre el resto del alquiler.",
        ),
    )

    # Another example expense not shared
    db.execute(
        "INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)",
        (
            ejem_job_id_gasto,
            "Ejem_Comida equipo en obra",
            "Comida",
            45.00,
            10.0,
            (today - timedelta(days=4)).isoformat(),
        ),
    )

    # --- Tareas (Tasks) ---
    # Get an existing job_id to link tasks to
    # ejem_job_id = db.execute("SELECT id FROM trabajos WHERE titulo = 'Ejem_Reparación eléctrica en obra'").fetchone()['id'] # Already fetched above
    ejem_autonomo_id = db.execute(
        "SELECT id FROM users WHERE username = 'Carlos Gomez'"
    ).fetchone()["id"]

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
            "Ejem_Instalar nuevo enchufe",
            "Instalación de enchufe doble en salón.",
            "Pendiente",
            (today + timedelta(days=7)).isoformat(),
            ejem_autonomo_id,
            "Pendiente",
            "Pendiente",
            0.00,
            None,
        ),
        (
            ejem_job_id,
            "Ejem_Comprar materiales",
            "Adquirir materiales para la reparación.",
            "Completada",
            (today - timedelta(days=2)).isoformat(),
            ejem_autonomo_id,
            "Efectivo",
            "Abonado",
            25.50,
            (today - timedelta(days=2)).isoformat(),
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
        db.execute(
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
            ),
        )

    # --- Job Material Installation Costs (Ejem) ---
    # Get existing material and service IDs
    ejem_material_id = db.execute(
        "SELECT id FROM materials WHERE name = 'Tornillos 5mm'"
    ).fetchone()["id"]
    ejem_service_id = db.execute(
        "SELECT id FROM services WHERE name = 'Instalación Eléctrica'"
    ).fetchone()["id"]

    job_install_costs_to_add = [
        (
            ejem_job_id,
            ejem_material_id,
            None,
            "Ejem_Costo de instalación de tornillos",
            5.00,
            10.00,
            (today + timedelta(days=1)).isoformat(),
            "Notas de instalación de tornillos.",
        ),
        (
            ejem_job_id,
            None,
            ejem_service_id,
            "Ejem_Costo de configuración eléctrica",
            20.00,
            30.00,
            (today + timedelta(days=2)).isoformat(),
            "Notas de configuración eléctrica.",
        ),
    ]
    for (
        job_id,
        material_id,
        service_id,
        description,
        cost,
        revenue,
        date,
        notes,
    ) in job_install_costs_to_add:
        db.execute(
            "INSERT INTO job_material_install_costs (job_id, material_id, service_id, description, cost, revenue, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, material_id, service_id, description, cost, revenue, date, notes),
        )

    # --- Gastos (Expenses) and Shared Expenses (Ejem) ---
    # Get existing job_id and freelancer IDs
    ejem_job_id_gasto = ejem_job_id  # Use the same example job ID
    carlos_id = db.execute(
        "SELECT id FROM users WHERE username = 'Carlos Gomez'"
    ).fetchone()["id"]
    sofia_id = db.execute(
        "SELECT id FROM users WHERE username = 'Sofia Lopez'"
    ).fetchone()["id"]

    # Example shared expense: a tool rental
    db.execute(
        "INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)",
        (
            ejem_job_id_gasto,
            "Ejem_Alquiler de furgoneta para transporte de material",
            "Transporte",
            120.00,
            21.0,
            (today - timedelta(days=5)).isoformat(),
        ),
    )
    gasto_furgoneta_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Carlos pays 70%
    db.execute(
        "INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)",
        (
            gasto_furgoneta_id,
            carlos_id,
            84.00,
            1,
            "Ejem_Carlos cubre la mayor parte del alquiler.",
        ),
    )
    # Sofia pays 30%
    db.execute(
        "INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)",
        (
            gasto_furgoneta_id,
            sofia_id,
            36.00,
            1,
            "Ejem_Sofía cubre el resto del alquiler.",
        ),
    )

    # Another example expense not shared
    db.execute(
        "INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)",
        (
            ejem_job_id_gasto,
            "Ejem_Comida equipo en obra",
            "Comida",
            45.00,
            10.0,
            (today - timedelta(days=4)).isoformat(),
        ),
    )

    db.commit()
    db.close()
    click.echo("Base de datos inicializada con un gran conjunto de datos de ejemplo.")


app.cli.add_command(init_db_command)


@click.command("import-csv-data")
def import_csv_data_command():
    """Import data from CSV files into the database."""
    db = get_db_connection()
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
                autonomo_role_id = cursor.execute(
                    "SELECT id FROM roles WHERE name = 'Autonomo'"
                ).fetchone()["id"]
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
                    existing_user = cursor.execute(
                        "SELECT id FROM users WHERE username = ? OR email = ?",
                        (username, email),
                    ).fetchone()
                    if not existing_user:
                        cursor.execute(
                            "INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, ?)",
                            (username, hashed_password, email, True),
                        )
                        user_id = cursor.execute(
                            "SELECT last_insert_rowid()"
                        ).fetchone()[0]
                        cursor.execute(
                            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                            (user_id, autonomo_role_id),
                        )

                        # Insert into freelancer_details
                        cursor.execute(
                            "INSERT INTO freelancer_details (id, category, specialty, city_province, address, web, phone, whatsapp, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
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
                            ),
                        )
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
                        existing_proveedor = cursor.execute(
                            "SELECT id FROM proveedores WHERE nombre = ?", (nombre,)
                        ).fetchone()
                        if not existing_proveedor:
                            cursor.execute(
                                "INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)",
                                (nombre, contacto, telefono, email, direccion, tipo),
                            )
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
                        cursor.execute(
                            "UPDATE services SET recommended_price = ? WHERE name = ?",
                            (recommended_price, service_name),
                        )
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

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self._is_active

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name):
        conn = get_db_connection()
        if not conn:
            return False

        has_perm = False
        try:
            with conn.cursor() as cursor:
                # Get user's roles
                cursor.execute(
                    "SELECT role_id FROM user_roles WHERE user_id = %s", (self.id,)
                )
                user_roles_data = cursor.fetchall()
                user_role_ids = [row["role_id"] for row in user_roles_data]

                if user_role_ids:
                    # Use a tuple for the IN clause, which is standard for psycopg2
                    query = "SELECT COUNT(p.id) FROM permissions p JOIN role_permissions rp ON p.id = rp.permission_id WHERE p.name = %s AND rp.role_id IN %s"
                    cursor.execute(query, (permission_name, tuple(user_role_ids)))
                    result = cursor.fetchone()
                    if result:
                        has_perm = result[0] > 0
        except Exception as e:
            print(f"Error checking permissions: {e}")
            # In case of an error, default to no permission for safety
            has_perm = False
        finally:
            if conn:
                conn.close()
        return has_perm


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn is None:
        print("Error: Could not connect to database for user loading.")
        return None  # Return None if connection fails
    cursor = conn.cursor()  # Get a cursor
    cursor.execute(
        "SELECT * FROM users WHERE id = %s", (user_id,)
    )  # Use cursor.execute and %s
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
        conn = get_db_connection()
        if conn is None:
            flash("Error: No se pudo conectar a la base de datos.", "danger")
            return render_template("login.html")  # Return to login page with error

        cursor = conn.cursor()  # Get a cursor
        cursor.execute(
            "SELECT * FROM users WHERE username = %s", (username,)
        )  # Use cursor.execute and %s
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


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/register/client", methods=["GET", "POST"])
def register_client():
    conn = get_db_connection()
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
        except psycopg2.IntegrityError:
            flash("Error: El nombre de usuario o el email ya existen.", "danger")
            conn.rollback()
        finally:
            if 'cursor' in locals() and cursor is not None: cursor.close()
            if conn is not None: conn.close()

    return render_template("register_client.html")

@app.route("/register/freelancer", methods=["GET", "POST"])
def register_freelancer():
    conn = get_db_connection()
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

            # Handle file uploads (placeholder)
            if 'project_files' in request.files:
                files = request.files.getlist('project_files')
                for file in files:
                    if file.filename == '':
                        continue
                    # TODO: Implement actual file saving logic here
                    # For example: filename = secure_filename(file.filename)
                    # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    # You might want to store file paths in the database as well

            conn.commit()
            flash(
                f'Usuario "{username}" registrado exitosamente como Autónomo. Ahora puedes iniciar sesión.',
                "success",
            )
            log_activity(user_id, "REGISTER_FREELANCER", f"New freelancer registered: {username}.")
            return redirect(url_for("login"))
        except psycopg2.IntegrityError:
            flash("Error: El nombre de usuario o el email ya existen.", "danger")
            conn.rollback()
        finally:
            if 'cursor' in locals() and cursor is not None: cursor.close()
            if conn is not None: conn.close()

    return render_template("register_freelancer.html")

@app.route("/register/provider", methods=["GET", "POST"])
def register_provider():
    conn = get_db_connection()
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

            # Handle file uploads (placeholder)
            if 'project_files' in request.files:
                files = request.files.getlist('project_files')
                for file in files:
                    if file.filename == '':
                        continue
                    # TODO: Implement actual file saving logic here
                    # For example: filename = secure_filename(file.filename)
                    # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    # You might want to store file paths in the database as well

            conn.commit()
            flash(
                f'Usuario "{username}" registrado exitosamente como Proveedor. Ahora puedes iniciar sesión.',
                "success",
            )
            log_activity(user_id, "REGISTER_PROVIDER", f"New provider registered: {username}.")
            return redirect(url_for("login"))
        except psycopg2.IntegrityError:
            flash("Error: El nombre de usuario o el email ya existen.", "danger")
            conn.rollback()
        finally:
            if 'cursor' in locals() and cursor is not None: cursor.close()
            if conn is not None: conn.close()

    return render_template("register_provider.html")

@app.route("/profile")
@login_required
def user_profile():
    conn = get_db_connection()
    if conn is None:
        flash("Error: No se pudo conectar a la base de datos.", "danger")
        return redirect(url_for("dashboard"))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = ?",
        (current_user.id,),
    )
    user_roles = cursor.fetchall()
    roles = [row["name"] for row in user_roles]
    cursor.close()
    conn.close()
    return render_template("users/profile.html", user=current_user, roles=roles)
