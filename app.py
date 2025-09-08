import sqlite3
import click
import csv # New import
import os # New import
import re # New import
import urllib.parse # New import
import psycopg2 # New import
import psycopg2.extras # New import
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app # Added current_app
from datetime import datetime, timedelta # Added timedelta for snooze
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps # New import for decorator

# Custom permission decorator
def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Necesitas iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('login'))
            if not current_user.has_permission(permission_name):
                flash(f'No tienes permiso para realizar esta acción: {permission_name}.', 'danger')
                return redirect(url_for('dashboard')) # Redirect to a safe page
            return f(*args, **kwargs)
        return decorated_function
    return decorator

app = Flask(__name__)
app.secret_key = 'grupokoal_super_secret_key'

def setup_new_database(conn, is_sqlite=False):
    """Sets up a new database with schema and essential data like roles and permissions."""
    cursor = conn.cursor()
    
    # 1. Create schema
    with current_app.open_resource('schema.sql', mode='r') as f:
        schema_sql = f.read()
        if is_sqlite:
            # Adjust schema for SQLite if needed
            schema_sql = schema_sql.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            schema_sql = schema_sql.replace('TEXT UNIQUE NOT NULL', 'TEXT UNIQUE NOT NULL COLLATE NOCASE')
            schema_sql = schema_sql.replace('TEXT', 'TEXT COLLATE NOCASE')
            schema_sql = schema_sql.replace('TIMESTAMP DEFAULT NOW()', 'DATETIME DEFAULT CURRENT_TIMESTAMP')
            schema_sql = schema_sql.replace('DOUBLE PRECISION', 'REAL')
            schema_sql = schema_sql.replace('NUMERIC', 'REAL')
            schema_sql = schema_sql.replace('JSONB', 'TEXT')
        else: # Adjust schema for PostgreSQL if needed
            # Handle BOOLEAN defaults using regex for robustness
            schema_sql = re.sub(r'BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE', schema_sql)
            schema_sql = re.sub(r'BOOLEAN DEFAULT 1', 'BOOLEAN DEFAULT TRUE', schema_sql)

            schema_sql = schema_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            schema_sql = schema_sql.replace('REAL', 'NUMERIC')
            # More specific TEXT replacements first
            schema_sql = schema_sql.replace('TEXT UNIQUE NOT NULL', 'VARCHAR UNIQUE NOT NULL')
            schema_sql = schema_sql.replace('TEXT UNIQUE', 'VARCHAR UNIQUE')
            schema_sql = schema_sql.replace('TEXT NOT NULL', 'VARCHAR NOT NULL')
            schema_sql = schema_sql.replace('TEXT', 'VARCHAR') # General TEXT to VARCHAR

        
        if is_sqlite:
            cursor.executescript(schema_sql)
        else:
            # For PostgreSQL, execute line by line to handle potential errors better
            # and to allow for comments and multiple statements per line
            for statement in schema_sql.split(';'):
                if statement.strip():
                    try:
                        cursor.execute(statement + ';')
                    except psycopg2.Error as e:
                        print(f"Error executing statement: {statement.strip()} - {e}")
                        conn.rollback()
                        raise # Re-raise the exception after logging
            conn.commit() # Commit after schema creation for PostgreSQL

    # 2. Insert roles
    roles_to_add = ['Admin', 'Oficinista', 'Autonomo', 'Cliente'] # Added Cliente role
    for role_name in roles_to_add:
        if is_sqlite:
            cursor.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", (role_name,))
        else:
            cursor.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (role_name,))
    conn.commit()
    
    # Fetch role IDs
    if is_sqlite:
        admin_role_id = cursor.execute("SELECT id FROM roles WHERE name = 'Admin'").fetchone()['id']
        oficinista_role_id = cursor.execute("SELECT id FROM roles WHERE name = 'Oficinista'").fetchone()['id']
        autonomo_role_id = cursor.execute("SELECT id FROM roles WHERE name = 'Autonomo'").fetchone()['id']
        cliente_role_id = cursor.execute("SELECT id FROM roles WHERE name = 'Cliente'").fetchone()['id']
    else:
        admin_role_id = cursor.execute("SELECT id FROM roles WHERE name = %s", ('Admin',)).fetchone()[0]
        oficinista_role_id = cursor.execute("SELECT id FROM roles WHERE name = %s", ('Oficinista',)).fetchone()[0]
        autonomo_role_id = cursor.execute("SELECT id FROM roles WHERE name = %s", ('Autonomo',)).fetchone()[0]
        cliente_role_id = cursor.execute("SELECT id FROM roles WHERE name = %s", ('Cliente',)).fetchone()[0]

    # 3. Insert permissions
    permissions_to_add = [
        'view_users', 'manage_users', 'view_freelancers', 'view_materials', 'manage_materials',
        'view_proveedores', 'manage_proveedores', 'view_financial_reports', 'manage_csv_import',
        'view_all_jobs', 'manage_all_jobs', 'view_own_jobs', 'manage_own_jobs',
        'view_all_tasks', 'manage_all_tasks', 'view_own_tasks', 'manage_own_tasks',
        'manage_notifications', 'create_quotes', 'upload_files' # New permissions
    ]
    for perm_name in permissions_to_add:
        if is_sqlite:
            cursor.execute("INSERT OR IGNORE INTO permissions (name) VALUES (?)", (perm_name,))
        else:
            cursor.execute("INSERT INTO permissions (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (perm_name,))
    conn.commit()

    # 4. Assign permissions to roles
    def assign_permission(role_id, perm_name):
        if is_sqlite:
            perm_id_row = cursor.execute("SELECT id FROM permissions WHERE name = ?", (perm_name,)).fetchone()
        else:
            cursor.execute("SELECT id FROM permissions WHERE name = %s", (perm_name,))
            perm_id_row = cursor.fetchone()

        if perm_id_row:
            perm_id = perm_id_row[0]
            if is_sqlite:
                cursor.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)", (role_id, perm_id))
            else:
                cursor.execute("INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s) ON CONFLICT (role_id, permission_id) DO NOTHING", (role_id, perm_id))

    # Admin gets all permissions
    for perm_name in permissions_to_add:
        assign_permission(admin_role_id, perm_name)

    # Oficinista permissions
    oficinista_perms = [
        'view_users', 'view_freelancers', 'view_materials', 'manage_materials',
        'view_proveedores', 'manage_proveedores', 'view_financial_reports',
        'view_all_jobs', 'manage_all_jobs', 'view_all_tasks', 'manage_all_tasks',
        'manage_notifications', 'create_quotes', 'upload_files' # Added new permissions
    ]
    for perm_name in oficinista_perms:
        assign_permission(oficinista_role_id, perm_name)

    # Autonomo permissions
    autonomo_perms = [
        'view_own_jobs', 'manage_own_jobs', 'view_own_tasks', 'manage_own_tasks',
        'manage_notifications', 'create_quotes', 'upload_files' # Added new permissions
    ]
    for perm_name in autonomo_perms:
        assign_permission(autonomo_role_id, perm_name)
    
    # Client permissions (view own jobs/quotes)
    cliente_perms = [
        'view_own_jobs', 'create_quotes' # Clients can create quotes
    ]
    for perm_name in cliente_perms:
        assign_permission(cliente_role_id, perm_name)

    conn.commit()
    cursor.close()
    print("Initialized new database with schema and roles.")


# --- Database Connection ---
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # Connect to PostgreSQL
        print("Attempting to connect to PostgreSQL...") # Debug print
        try:
            # Parse the DATABASE_URL to extract components
            result = urllib.parse.urlparse(DATABASE_URL)
            username = result.username
            password = result.password
            database = result.path[1:].strip() # Remove leading '/' and trim whitespace
            hostname = result.hostname
            port = result.port

            # Construct connection string with trimmed database name
            conn = psycopg2.connect(
                host=hostname,
                port=port,
                database=database,
                user=username,
                password=password
            )
            conn.autocommit = False # Manage transactions manually
            
            conn.cursor_factory = psycopg2.extras.DictCursor
            
            # Check if tables exist, if not, initialize
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'users');")
            tables_exist = cursor.fetchone()[0]
            cursor.close()

            if not tables_exist:
                print("PostgreSQL tables not found. Initializing new PostgreSQL database...")
                with current_app.app_context(): # Use current_app
                    setup_new_database(conn, is_sqlite=False)
                print("PostgreSQL database initialized.")
            
            print("Successfully connected to PostgreSQL.") # Debug print
            return conn
        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL: {e}") # Debug print
            print("Falling back to SQLite for local development (PostgreSQL connection failed).") # Debug print
            # Fallback to SQLite for local development if PostgreSQL connection fails
            # This is a fallback for local dev, not for Render deployment
            db_path = 'database.db'
            db_is_new = not os.path.exists(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute('PRAGMA foreign_keys = ON')
            conn.row_factory = sqlite3.Row
            if db_is_new:
                print("SQLite database not found. Initializing new SQLite database...")
                with current_app.app_context(): # Use current_app
                    setup_new_database(conn, is_sqlite=True)
                print("SQLite database initialized.")
            return conn
    else:
        print("DATABASE_URL not set. Connecting to SQLite for local development.") # Debug print
        # Fallback to SQLite for local development if DATABASE_URL is not set
        db_path = 'database.db'
        db_is_new = not os.path.exists(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.row_factory = sqlite3.Row
        if db_is_new:
            print("SQLite database not found. Initializing new SQLite database...")
            with current_app.app_context(): # Use current_app
                setup_new_database(conn, is_sqlite=True)
            print("SQLite database initialized.")
        return conn

# --- Activity Logging Function ---
def log_activity(user_id, action, details=None):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    timestamp = datetime.now().isoformat()
    cursor.execute('INSERT INTO activity_log (user_id, action, details, timestamp) VALUES (%s, %s, %s, %s)',
                 (user_id, action, details, timestamp)) # Use cursor.execute and %s
    conn.commit()
    cursor.close() # Close cursor
    conn.close() # Close connection

# --- Notification Generation Function ---
def generate_notifications_for_user(user_id):
    conn = get_db_connection()
    if not conn:
        return

    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        # 1. Upcoming Jobs
        cursor.execute(
            "SELECT id, titulo, fecha_visita FROM trabajos WHERE fecha_visita BETWEEN date(%s) AND date(%s, '+7 days') AND estado != 'Finalizado'",
            (today, today)
        )
        upcoming_jobs = cursor.fetchall()
        for job in upcoming_jobs:
            message = f"El trabajo '{job['titulo']}' está programado para el {job['fecha_visita']}."
            cursor.execute(
                "SELECT id FROM notifications WHERE user_id = %s AND type = 'job_reminder' AND related_id = %s AND message = %s",
                (user_id, job['id'], message)
            )
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (%s, %s, %s, %s, %s)',
                    (user_id, message, 'job_reminder', job['id'], datetime.now().isoformat())
                )

        # 2. Overdue Tasks
        cursor.execute(
            "SELECT t.id, t.titulo, t.fecha_limite, tr.titulo as trabajo_titulo FROM tareas t "
            "JOIN trabajos tr ON t.trabajo_id = tr.id "
            "WHERE t.fecha_limite < %s AND t.estado != 'Completada' AND t.autonomo_id = %s",
            (today, user_id)
        )
        overdue_tasks = cursor.fetchall()
        for task in overdue_tasks:
            message = f"La tarea '{task['titulo']}' del trabajo '{task['trabajo_titulo']}' está atrasada desde el {task['fecha_limite']}."
            cursor.execute(
                "SELECT id FROM notifications WHERE user_id = %s AND type = 'task_overdue' AND related_id = %s AND message = %s",
                (user_id, task['id'], message)
            )
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (%s, %s, %s, %s, %s)',
                    (user_id, message, 'task_overdue', task['id'], datetime.now().isoformat())
                )

        # 3. Low Stock Materials
        cursor.execute("SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = %s", (user_id,))
        user_roles = cursor.fetchall()
        role_names = [role['name'] for role in user_roles]

        if 'Admin' in role_names or 'Oficinista' in role_names:
            cursor.execute("SELECT id, name, current_stock, min_stock_level FROM materials WHERE current_stock <= min_stock_level")
            low_stock_materials = cursor.fetchall()
            for material in low_stock_materials:
                message = f"El material '{material['name']}' tiene bajo stock: {material['current_stock']} (Mínimo: {material['min_stock_level']})."
                cursor.execute(
                    "SELECT id FROM notifications WHERE user_id = %s AND type = 'low_stock' AND related_id = %s AND message = %s",
                    (user_id, material['id'], message)
                )
                if not cursor.fetchone():
                    cursor.execute(
                        'INSERT INTO notifications (user_id, message, type, related_id, timestamp) VALUES (%s, %s, %s, %s, %s)',
                        (user_id, message, 'low_stock', material['id'], datetime.now().isoformat())
                    )
        
        conn.commit()
    except (psycopg2.Error, sqlite3.Error) as e:
        print(f"Error generating notifications: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

# --- Database Initialization Command ---
@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables with a large set of sample data."""
    db = get_db_connection()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit() # Commit schema changes
    db.close() # Close connection to apply schema changes
    db = get_db_connection() # Reopen connection with new schema

    # --- Roles ---
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Admin')")
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Oficinista')")
    db.execute("INSERT OR IGNORE INTO roles (name) VALUES ('Autonomo')")
    db.commit()
    admin_role_id = db.execute("SELECT id FROM roles WHERE name = 'Admin'").fetchone()['id']
    oficinista_role_id = db.execute("SELECT id FROM roles WHERE name = 'Oficinista'").fetchone()['id']
    autonomo_role_id = db.execute("SELECT id FROM roles WHERE name = 'Autonomo'").fetchone()['id']

    # --- Permissions ---
    permissions_to_add = [
        'view_users', 'manage_users', 'view_freelancers', 'view_materials', 'manage_materials',
        'view_proveedores', 'manage_proveedores', 'view_financial_reports', 'manage_csv_import',
        'view_all_jobs', 'manage_all_jobs', 'view_own_jobs', 'manage_own_jobs',
        'view_all_tasks', 'manage_all_tasks', 'view_own_tasks', 'manage_own_tasks',
        'manage_notifications'
    ]
    for perm_name in permissions_to_add:
        db.execute("INSERT OR IGNORE INTO permissions (name) VALUES (?)", (perm_name,))
    db.commit()

    # Assign permissions to roles
    def assign_permission(role_id, perm_name):
        perm_id = db.execute("SELECT id FROM permissions WHERE name = ?", (perm_name,)).fetchone()['id']
        db.execute("INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)", (role_id, perm_id))

    # Admin gets all permissions
    for perm_name in permissions_to_add:
        assign_permission(admin_role_id, perm_name)

    # Oficinista permissions
    oficinista_perms = [
        'view_users', 'view_freelancers', 'view_materials', 'manage_materials',
        'view_proveedores', 'manage_proveedores', 'view_financial_reports',
        'view_all_jobs', 'manage_all_jobs', 'view_all_tasks', 'manage_all_tasks',
        'manage_notifications'
    ]
    for perm_name in oficinista_perms:
        assign_permission(oficinista_role_id, perm_name)

    # Autonomo permissions
    autonomo_perms = [
        'view_own_jobs', 'manage_own_jobs', 'view_own_tasks', 'manage_own_tasks',
        'manage_notifications'
    ]
    for perm_name in autonomo_perms:
        assign_permission(autonomo_role_id, perm_name)
    db.commit()

    # --- Users ---
    users_to_add = [
        ('jorge moreno', '6336604j', 'admin@grupokoal.com', admin_role_id),
        ('Laura Ventas', 'password123', 'laura.ventas@grupokoal.com', oficinista_role_id),
        ('Carlos Gomez', 'password123', 'carlos.gomez@autonomo.com', autonomo_role_id),
        ('Sofia Lopez', 'password123', 'sofia.lopez@autonomo.com', autonomo_role_id),
        ('Ana Torres', 'password123', 'ana.torres@autonomo.com', autonomo_role_id)
    ]
    for username, password, email, role_id in users_to_add:
        hashed_password = generate_password_hash(password)
        db.execute('INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, ?)', (username, hashed_password, email, True))
        user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.execute('INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)', (user_id, role_id))
    db.commit()
    carlos_id = db.execute("SELECT id FROM users WHERE username = 'Carlos Gomez'").fetchone()['id']
    sofia_id = db.execute("SELECT id FROM users WHERE username = 'Sofia Lopez'").fetchone()['id']
    ana_id = db.execute("SELECT id FROM users WHERE username = 'Ana Torres'").fetchone()['id']

    # --- Clients ---
    db.execute("INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)", ('Constructora XYZ', 'Calle Falsa 123, Valencia', '960123456', 'contacto@constructoraxyz.com'))
    db.execute("INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)", ('Reformas El Sol', 'Avenida del Puerto 50, Valencia', '960987654', 'info@reformaselsol.es'))
    db.execute("INSERT INTO clients (nombre, direccion, telefono, email) VALUES (?, ?, ?, ?)", ('Comunidad de Vecinos El Roble', 'Plaza del Arbol 1, Silla', '961231234', 'admin@roble.com'))
    db.commit()
    client1_id = db.execute("SELECT id FROM clients WHERE nombre = 'Constructora XYZ'").fetchone()['id']
    client2_id = db.execute("SELECT id FROM clients WHERE nombre = 'Reformas El Sol'").fetchone()['id']
    client3_id = db.execute("SELECT id FROM clients WHERE nombre = 'Comunidad de Vecinos El Roble'").fetchone()['id']

    # --- Proveedores ---
    proveedores_to_add = [
        ('Suministros Eléctricos del Turia', 'Ana García', '963123456', 'info@electricidadturia.com', 'Calle de la Luz 10, Valencia', 'Electricidad'),
        ('Fontanería Express SL', 'Pedro Ruiz', '963987654', 'contacto@fontaneriaexpress.es', 'Av. del Agua 5, Valencia', 'Fontanería'),
        ('Almacenes de Construcción Levante', 'Marta Pérez', '960112233', 'ventas@almaceneslevante.com', 'Pol. Ind. La Paz, Valencia', 'Materiales de Construcción'),
        ('Herramientas Profesionales Vlc', 'Luis Torres', '963554433', 'pedidos@herramientasvlc.com', 'C/ Herramientas 22, Valencia', 'Herramientas'),
        ('Pinturas Color Vivo', 'Elena Sanz', '963778899', 'info@pinturascolorvivo.com', 'Gran Vía 15, Valencia', 'Pintura'),
        ('Climatización Total', 'Javier Mora', '963210987', 'comercial@climatizaciontotal.com', 'C/ Aire 3, Valencia', 'Climatización'),
        ('Cristalería Rápida', 'Carmen Díaz', '963445566', 'presupuestos@cristaleriarapida.com', 'Av. del Cristal 1, Valencia', 'Cristalería'),
        ('Carpintería Artesanal', 'Roberto Gil', '963667788', 'info@carpinteriaartesanal.com', 'C/ Madera 7, Valencia', 'Carpintería'),
        ('Cerrajeros 24h', 'Sofía Navarro', '963889900', 'urgencias@cerrajeros24h.com', 'C/ Llave 1, Valencia', 'Cerrajería'),
        ('Reformas Integrales Valencia', 'Miguel Ángel', '963112233', 'info@reformasin.com', 'C/ Obra 5, Valencia', 'Reformas')
    ]
    for nombre, contacto, telefono, email, direccion, tipo in proveedores_to_add:
        db.execute("INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)",
                   (nombre, contacto, telefono, email, direccion, tipo))

    # --- Materials & Services ---
    materials_to_add = [
        ('Tornillos 5mm', 'Caja de 100 unidades', 20, 5.50, 6.00, 5.00),
        ('Placa de Pladur', 'Placa de 120x80cm', 20, 12.75, 13.50, 12.00),
        ('Saco de Cemento', 'Saco de 25kg', 20, 8.00, 8.50, 7.80),
        ('Pintura Blanca (10L)', 'Pintura plástica interior', 20, 45.00, 48.00, 42.00),
        ('Brocha (50mm)', 'Brocha para pintura', 20, 7.50, 8.00, 7.00),
        ('Cable Eléctrico (100m)', 'Cable unifilar 2.5mm', 20, 60.00, 65.00, 58.00),
        ('Enchufe Doble', 'Enchufe de pared doble', 20, 3.20, 3.50, 3.00),
        ('Tubería PVC (3m)', 'Tubería de desagüe 50mm', 20, 15.00, 16.00, 14.50),
        ('Grifo Monomando', 'Grifo para lavabo', 20, 35.00, 38.00, 33.00),
        ('Azulejo Blanco (m2)', 'Azulejo cerámico 30x30cm', 20, 18.00, 19.00, 17.50),
        ('Silicona (tubo)', 'Sellador multiusos', 20, 4.50, 5.00, 4.20),
        ('Martillo', 'Martillo de uña', 20, 12.00, 13.00, 11.50),
        ('Taladro Percutor', 'Taladro con función percutora', 20, 85.00, 90.00, 80.00),
        ('Lija (paquete)', 'Paquete de lijas grano 120', 20, 6.00, 6.50, 5.80),
        ('Guantes de Trabajo', 'Guantes de protección', 20, 3.00, 3.20, 2.80),
        ('Masilla para Madera', 'Masilla reparadora', 20, 9.00, 9.50, 8.80),
        ('Cinta Aislante', 'Cinta aislante eléctrica', 20, 2.50, 2.80, 2.30),
        ('Nivel (60cm)', 'Nivel de burbuja', 20, 25.00, 27.00, 24.00),
        ('Sierra de Calar', 'Sierra eléctrica para cortes curvos', 20, 55.00, 58.00, 52.00),
        ('Destornillador Set', 'Set de destornilladores variados', 20, 18.00, 19.00, 17.00)
    ]
    for name, desc, stock, price, recommended_price, last_sold_price in materials_to_add:
        db.execute("INSERT INTO materials (name, description, current_stock, unit_price, recommended_price, last_sold_price) VALUES (?, ?, ?, ?, ?, ?)",
                   (name, desc, stock, price, recommended_price, last_sold_price))

    db.execute("INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Instalación Eléctrica', 'Punto de luz completo', 50.00, 55.00, 48.00)")
    db.execute("INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Fontanería', 'Instalación de grifo', 40.00, 45.00, 38.00)")
    db.execute("INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Ejem_Servicio de Pintura', 'Pintura de pared interior', 30.00, 35.00, 28.00)")
    db.execute("INSERT INTO services (name, description, price, recommended_price, last_sold_price) VALUES ('Ejem_Servicio de Albañilería', 'Reparación de muro', 70.00, 75.00, 68.00)")

    # --- Trabajos (Jobs) ---
    # --- Trabajos (Jobs) ---
    from datetime import date, timedelta
    import random
    today = date.today()

    # Insert a specific example job first to get its ID
    db.execute("INSERT INTO trabajos (client_id, autonomo_id, titulo, descripcion, estado, presupuesto, vat_rate, fecha_visita, job_difficulty_rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
               (client1_id, carlos_id, 'Ejem_Reparación eléctrica en obra', 'Revisar cuadro eléctrico principal (Ejemplo)', 'En Progreso', 500.00, 21.0, (today + timedelta(days=2)).isoformat(), 3))
    ejem_job_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    jobs_to_add = [
        (client2_id, sofia_id, 'Instalación de 3 grifos', 'Baño y cocina de la reforma', 'Pendiente', 5, random.randint(1, 5)),
        (client1_id, None, 'Pintar oficina', 'Pintar paredes de oficina de 20m2', 'Presupuestado', 10, random.randint(1, 5)),
        (client3_id, ana_id, 'Cambio de bajante', 'Sustituir bajante comunitaria', 'Pendiente', 3, random.randint(1, 5)),
        (client2_id, carlos_id, 'Instalar 5 puntos de luz', 'Nuevos puntos en falso techo', 'En Progreso', 1, random.randint(1, 5)),
        (client1_id, sofia_id, 'Revisión fontanería (URGENTE)', 'Fuga en baño de planta 2', 'En Progreso', -2, random.randint(1, 5)),
        (client3_id, None, 'Presupuesto reforma portal', 'Medir y evaluar estado', 'Presupuestado', -5, random.randint(1, 5)),
        (client2_id, ana_id, 'Alicatado de baño', 'Poner azulejos en pared de ducha', 'Finalizado', -15, random.randint(1, 5)),
        (client1_id, carlos_id, 'Instalación de aire acondicionado', 'Split en salón principal', 'Finalizado', -30, random.randint(1, 5)),
        (client3_id, sofia_id, 'Reparar persiana', 'La persiana del dormitorio no baja', 'Pendiente', 7, random.randint(1, 5)),
        (client1_id, ana_id, 'Mantenimiento ascensor', 'Revisión mensual programada', 'Pendiente', 12, random.randint(1, 5)),
        (client2_id, None, 'Presupuesto pintura exterior', 'Evaluar fachada y medir metros', 'Presupuestado', 4, random.randint(1, 5)),
        (client3_id, carlos_id, 'Solucionar apagón', 'El diferencial salta constantemente', 'En Progreso', 0, random.randint(1, 5)),
        (client1_id, sofia_id, 'Cambiar cisterna', 'La cisterna del baño de invitados pierde agua', 'Pendiente', 8, random.randint(1, 5)),
        (client2_id, ana_id, 'Instalar tarima flotante', 'Habitación de 15m2', 'Presupuestado', 20, random.randint(1, 5)),
        (client3_id, carlos_id, 'Revisión de gas', 'Inspección periódica obligatoria', 'Finalizado', -45, random.randint(1, 5)),
        (client1_id, None, 'Limpieza de obra', 'Retirar escombros y limpiar zona', 'Pendiente', 6, random.randint(1, 5)),
        (client2_id, sofia_id, 'Montaje de muebles de cocina', 'Montar 4 módulos y encimera', 'En Progreso', 1, random.randint(1, 5)),
        (client3_id, ana_id, 'Reparación de goteras', 'Goteras en el techo del ático', 'Pendiente', 9, random.randint(1, 5)),
        (client1_id, carlos_id, 'Instalar videoportero', 'Sustituir telefonillo antiguo', 'Finalizado', -10, random.randint(1, 5)),
        (client1_id, carlos_id, 'Revisión instalación gas', 'Inspección anual obligatoria', 'Pendiente', 15, random.randint(1, 5)),
        (client2_id, sofia_id, 'Reparación tejado', 'Sustitución de tejas rotas', 'Presupuestado', 25, random.randint(1, 5)),
        (client3_id, ana_id, 'Instalación de alarma', 'Sistema de seguridad para vivienda', 'En Progreso', 3, random.randint(1, 5)),
        (client1_id, None, 'Presupuesto reforma cocina', 'Diseño y presupuesto de cocina', 'Presupuestado', 18, random.randint(1, 5)),
        (client2_id, carlos_id, 'Desatasco de tubería', 'Desatasco en baño principal', 'Finalizado', -1, random.randint(1, 5)),
        (client3_id, sofia_id, 'Cambio de cerradura', 'Sustitución de bombín de seguridad', 'Pendiente', 10, random.randint(1, 5)),
        (client1_id, ana_id, 'Instalación de termo eléctrico', 'Sustitución de termo antiguo', 'En Progreso', 0, random.randint(1, 5)),
        (client2_id, None, 'Revisión de caldera', 'Mantenimiento preventivo', 'Pendiente', 22, random.randint(1, 5)),
        (client3_id, carlos_id, 'Montaje de pérgola', 'Instalación de pérgola en terraza', 'Finalizado', -7, random.randint(1, 5)),
        (client1_id, sofia_id, 'Reparación de gotera en techo', 'Localizar y reparar origen de gotera', 'En Progreso', -3, random.randint(1, 5)),
        (client2_id, ana_id, 'Instalación de suelo laminado', 'Salón de 30m2', 'Presupuestado', 28, random.randint(1, 5)),
        (client3_id, None, 'Presupuesto instalación placas solares', 'Estudio de viabilidad', 'Pendiente', 14, random.randint(1, 5)),
        (client1_id, carlos_id, 'Revisión de extintores', 'Mantenimiento anual', 'Finalizado', -60, random.randint(1, 5)),
        (client2_id, sofia_id, 'Reparación de puerta de garaje', 'Ajuste de motor y guías', 'En Progreso', -10, random.randint(1, 5)),
        (client3_id, ana_id, 'Instalación de antena TV', 'Antena parabólica para canales satélite', 'Pendiente', 11, random.randint(1, 5)),
        (client1_id, None, 'Limpieza de cristales en altura', 'Edificio de oficinas', 'Presupuestado', 19, random.randint(1, 5)),
        (client2_id, carlos_id, 'Reparación de bomba de agua', 'Bomba de pozo', 'En Progreso', -20, random.randint(1, 5)),
        (client3_id, sofia_id, 'Instalación de mampara de ducha', 'Mampara de cristal templado', 'Finalizado', -5, random.randint(1, 5)),
        (client1_id, ana_id, 'Revisión de sistema de riego', 'Jardín comunitario', 'Pendiente', 25, random.randint(1, 5)),
        (client2_id, None, 'Presupuesto reforma integral', 'Vivienda de 90m2', 'Presupuestado', 30, random.randint(1, 5))
    ]
    for client, autonomo, titulo, desc, estado, delta, difficulty in jobs_to_add:
        fecha = today + timedelta(days=delta)
        presupuesto = round(random.uniform(100, 2000), 2)
        db.execute("INSERT INTO trabajos (client_id, autonomo_id, titulo, descripcion, estado, presupuesto, fecha_visita, job_difficulty_rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (client, autonomo, titulo, desc, estado, presupuesto, fecha.isoformat(), difficulty))

    # --- Tareas (Tasks) ---
    # Get an existing job_id to link tasks to
    ejem_autonomo_id = db.execute("SELECT id FROM users WHERE username = 'Carlos Gomez'").fetchone()['id']

    tareas_to_add = [
        (ejem_job_id, 'Ejem_Revisar cableado', 'Revisión completa del cableado principal.', 'En Progreso', (today + timedelta(days=3)).isoformat(), ejem_autonomo_id, 'Tarjeta', 'Abonado', 50.00, (today + timedelta(days=1)).isoformat()),
        (ejem_job_id, 'Ejem_Instalar nuevo enchufe', 'Instalación de enchufe doble en salón.', 'Pendiente', (today + timedelta(days=7)).isoformat(), ejem_autonomo_id, 'Pendiente', 'Pendiente', 0.00, None),
        (ejem_job_id, 'Ejem_Comprar materiales', 'Adquirir materiales para la reparación.', 'Completada', (today - timedelta(days=2)).isoformat(), ejem_autonomo_id, 'Efectivo', 'Abonado', 25.50, (today - timedelta(days=2)).isoformat()),
    ]
    for trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago in tareas_to_add:
        db.execute("INSERT INTO tareas (trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago))

    # --- Job Material Installation Costs (Ejem) ---
    # Get existing material and service IDs
    ejem_material_id = db.execute("SELECT id FROM materials WHERE name = 'Tornillos 5mm'").fetchone()['id']
    ejem_service_id = db.execute("SELECT id FROM services WHERE name = 'Instalación Eléctrica'").fetchone()['id']

    job_install_costs_to_add = [
        (ejem_job_id, ejem_material_id, None, 'Ejem_Costo de instalación de tornillos', 5.00, 10.00, (today + timedelta(days=1)).isoformat(), 'Notas de instalación de tornillos.'),
        (ejem_job_id, None, ejem_service_id, 'Ejem_Costo de configuración eléctrica', 20.00, 30.00, (today + timedelta(days=2)).isoformat(), 'Notas de configuración eléctrica.'),
    ]
    for job_id, material_id, service_id, description, cost, revenue, date, notes in job_install_costs_to_add:
        db.execute("INSERT INTO job_material_install_costs (job_id, material_id, service_id, description, cost, revenue, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (job_id, material_id, service_id, description, cost, revenue, date, notes))

    # --- Gastos (Expenses) and Shared Expenses (Ejem) ---
    # Get existing job_id and freelancer IDs
    ejem_job_id_gasto = ejem_job_id # Use the same example job ID
    carlos_id = db.execute("SELECT id FROM users WHERE username = 'Carlos Gomez'").fetchone()['id']
    sofia_id = db.execute("SELECT id FROM users WHERE username = 'Sofia Lopez'").fetchone()['id']

    # Example shared expense: a tool rental
    db.execute(
        'INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)',
        (ejem_job_id_gasto, 'Ejem_Alquiler de furgoneta para transporte de material', 'Transporte', 120.00, 21.0, (today - timedelta(days=5)).isoformat())
    )
    gasto_furgoneta_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    # Carlos pays 70%
    db.execute(
        'INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)',
        (gasto_furgoneta_id, carlos_id, 84.00, 1, 'Ejem_Carlos cubre la mayor parte del alquiler.')
    )
    # Sofia pays 30%
    db.execute(
        'INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)',
        (gasto_furgoneta_id, sofia_id, 36.00, 1, 'Ejem_Sofía cubre el resto del alquiler.')
    )

    # Another example expense not shared
    db.execute(
        'INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)',
        (ejem_job_id_gasto, 'Ejem_Comida equipo en obra', 'Comida', 45.00, 10.0, (today - timedelta(days=4)).isoformat())
    )

    # --- Tareas (Tasks) ---
    # Get an existing job_id to link tasks to
    # ejem_job_id = db.execute("SELECT id FROM trabajos WHERE titulo = 'Ejem_Reparación eléctrica en obra'").fetchone()['id'] # Already fetched above
    ejem_autonomo_id = db.execute("SELECT id FROM users WHERE username = 'Carlos Gomez'").fetchone()['id']

    tareas_to_add = [
        (ejem_job_id, 'Ejem_Revisar cableado', 'Revisión completa del cableado principal.', 'En Progreso', (today + timedelta(days=3)).isoformat(), ejem_autonomo_id, 'Tarjeta', 'Abonado', 50.00, (today + timedelta(days=1)).isoformat()),
        (ejem_job_id, 'Ejem_Instalar nuevo enchufe', 'Instalación de enchufe doble en salón.', 'Pendiente', (today + timedelta(days=7)).isoformat(), ejem_autonomo_id, 'Pendiente', 'Pendiente', 0.00, None),
        (ejem_job_id, 'Ejem_Comprar materiales', 'Adquirir materiales para la reparación.', 'Completada', (today - timedelta(days=2)).isoformat(), ejem_autonomo_id, 'Efectivo', 'Abonado', 25.50, (today - timedelta(days=2)).isoformat()),
    ]
    for trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago in tareas_to_add:
        db.execute("INSERT INTO tareas (trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago))

    # --- Job Material Installation Costs (Ejem) ---
    # Get existing material and service IDs
    ejem_material_id = db.execute("SELECT id FROM materials WHERE name = 'Tornillos 5mm'").fetchone()['id']
    ejem_service_id = db.execute("SELECT id FROM services WHERE name = 'Instalación Eléctrica'").fetchone()['id']

    job_install_costs_to_add = [
        (ejem_job_id, ejem_material_id, None, 'Ejem_Costo de instalación de tornillos', 5.00, 10.00, (today + timedelta(days=1)).isoformat(), 'Notas de instalación de tornillos.'),
        (ejem_job_id, None, ejem_service_id, 'Ejem_Costo de configuración eléctrica', 20.00, 30.00, (today + timedelta(days=2)).isoformat(), 'Notas de configuración eléctrica.'),
    ]
    for job_id, material_id, service_id, description, cost, revenue, date, notes in job_install_costs_to_add:
        db.execute("INSERT INTO job_material_install_costs (job_id, material_id, service_id, description, cost, revenue, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (job_id, material_id, service_id, description, cost, revenue, date, notes))

    # --- Gastos (Expenses) and Shared Expenses (Ejem) ---
    # Get existing job_id and freelancer IDs
    ejem_job_id_gasto = ejem_job_id # Use the same example job ID
    carlos_id = db.execute("SELECT id FROM users WHERE username = 'Carlos Gomez'").fetchone()['id']
    sofia_id = db.execute("SELECT id FROM users WHERE username = 'Sofia Lopez'").fetchone()['id']

    # Example shared expense: a tool rental
    db.execute(
        'INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)',
        (ejem_job_id_gasto, 'Ejem_Alquiler de furgoneta para transporte de material', 'Transporte', 120.00, 21.0, (today - timedelta(days=5)).isoformat())
    )
    gasto_furgoneta_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    # Carlos pays 70%
    db.execute(
        'INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)',
        (gasto_furgoneta_id, carlos_id, 84.00, 1, 'Ejem_Carlos cubre la mayor parte del alquiler.')
    )
    # Sofia pays 30%
    db.execute(
        'INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)',
        (gasto_furgoneta_id, sofia_id, 36.00, 1, 'Ejem_Sofía cubre el resto del alquiler.')
    )

    # Another example expense not shared
    db.execute(
        'INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)',
        (ejem_job_id_gasto, 'Ejem_Comida equipo en obra', 'Comida', 45.00, 10.0, (today - timedelta(days=4)).isoformat())
    )

    # --- Job Material Installation Costs (Ejem) ---
    # Get existing material and service IDs
    ejem_material_id = db.execute("SELECT id FROM materials WHERE name = 'Tornillos 5mm'").fetchone()['id']
    ejem_service_id = db.execute("SELECT id FROM services WHERE name = 'Instalación Eléctrica'").fetchone()['id']

    job_install_costs_to_add = [
        (ejem_job_id, ejem_material_id, None, 'Ejem_Costo de instalación de tornillos', 5.00, 10.00, (today + timedelta(days=1)).isoformat(), 'Notas de instalación de tornillos.'),
        (ejem_job_id, None, ejem_service_id, 'Ejem_Costo de configuración eléctrica', 20.00, 30.00, (today + timedelta(days=2)).isoformat(), 'Notas de configuración eléctrica.'),
    ]
    for job_id, material_id, service_id, description, cost, revenue, date, notes in job_install_costs_to_add:
        db.execute("INSERT INTO job_material_install_costs (job_id, material_id, service_id, description, cost, revenue, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (job_id, material_id, service_id, description, cost, revenue, date, notes))

    db.commit()
    db.close()
    click.echo('Base de datos inicializada con un gran conjunto de datos de ejemplo.')


app.cli.add_command(init_db_command)

@click.command('import-csv-data')
def import_csv_data_command():
    """Import data from CSV files into the database."""
    db = get_db_connection()
    
    # --- Import Autonomos (Users) ---
    autonomos_csv_path = r'C:\Users\info\OneDrive\Escritorio\gestion_avisos\datos de distribuidores y autonomos\autonomos_y_servicios_valencia.csv'
    try:
        with open(autonomos_csv_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            autonomo_role_id = db.execute("SELECT id FROM roles WHERE name = 'Autonomo'").fetchone()['id']
            for row in reader:
                username = row['Nombre'].strip()
                email = row['Email'].strip() if row['Email'].strip() else f"{username.replace(' ', '.').lower()}@autonomo.com"
                password = "password123" # Default password
                hashed_password = generate_password_hash(password)

                # Check if user already exists
                existing_user = db.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchone()
                if not existing_user:
                    db.execute('INSERT INTO users (username, password_hash, email, is_active) VALUES (?, ?, ?, ?)',
                               (username, hashed_password, email, True))
                    user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
                    db.execute('INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)', (user_id, autonomo_role_id))
                    
                    # Insert into freelancer_details
                    db.execute(
                        'INSERT INTO freelancer_details (id, category, specialty, city_province, address, web, phone, whatsapp, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (
                            user_id,
                            row['Categoria'].strip(),
                            row['Especialidad'].strip(),
                            row['Ciudad/Provincia'].strip(),
                            row['Direccion'].strip(),
                            row['Web'].strip(),
                            row['Telefono'].strip(),
                            row['WhatsApp'].strip(),
                            row['Notas'].strip(),
                            row['FuenteURL'].strip(),
                            0.0, # Default normal rate
                            0.0, # Default tier2 rate
                            0.0,  # Default tier3 rate
                            5.0 # Example difficulty surcharge rate
                        )
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
    proveedores_dir = r'C:\Users\info\OneDrive\Escritorio\gestion_avisos\datos de distribuidores y autonomos'
    proveedores_files = [f for f in os.listdir(proveedores_dir) if f.startswith('proveedores_') and f.endswith('.csv')]

    for p_file in proveedores_files:
        p_file_path = os.path.join(proveedores_dir, p_file)
        try:
            with open(p_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    nombre = row['Nombre'].strip()
                    contacto = row['Especialidad'].strip() if row['Especialidad'].strip() else ""
                    telefono = row['Telefono'].strip()
                    email = row['Email'].strip()
                    direccion = row['Direccion'].strip()
                    tipo = row['Categoria'].strip()

                    # Check if proveedor already exists
                    existing_proveedor = db.execute("SELECT id FROM proveedores WHERE nombre = ?", (nombre,)).fetchone()
                    if not existing_proveedor:
                        db.execute('INSERT INTO proveedores (nombre, contacto, telefono, email, direccion, tipo) VALUES (?, ?, ?, ?, ?, ?)',
                                   (nombre, contacto, telefono, email, direccion, tipo))
                        click.echo(f"Imported proveedor: {nombre} from {p_file}")
                    else:
                        click.echo(f"Proveedor already exists (skipped): {nombre} from {p_file}")
            db.commit()
        except FileNotFoundError:
            click.echo(f"Error: Proveedor CSV file not found at {p_file_path}")
        except Exception as e:
            click.echo(f"Error importing proveedores from {p_file}: {e}")
            db.rollback()
    
    # --- Import Service Recommended Prices ---
    market_study_dir = r'C:\Users\info\OneDrive\Escritorio\gestion_avisos\datos de distribuidores y autonomos'
    market_study_files = [
        'grupokoal_PRICEBOOK_recomendado_Valencia_2025.csv',
        'grupokoal_estudio_mercado_precios_valencia_2025.csv'
    ]

    for ms_file_name in market_study_files:
        ms_file_path = os.path.join(market_study_dir, ms_file_name)
        try:
            with open(ms_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    service_name = row['Servicio'].strip()
                    # Use Precio_objetivo for recommended_price
                    recommended_price = float(row['Precio_objetivo']) if 'Precio_objetivo' in row and row['Precio_objetivo'] else 0.0

                    # Update the service in the database
                    db.execute('UPDATE services SET recommended_price = ? WHERE name = ?',
                               (recommended_price, service_name))
                    if db.rowcount > 0:
                        click.echo(f"Updated recommended price for service: {service_name} from {ms_file_name}")
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
login_manager.login_view = 'login'

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
                cursor.execute("SELECT role_id FROM user_roles WHERE user_id = %s", (self.id,))
                user_roles_data = cursor.fetchall()
                user_role_ids = [row['role_id'] for row in user_roles_data]

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
    cursor = conn.cursor() # Get a cursor
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,)) # Use cursor.execute and %s
    user_data = cursor.fetchone() # Fetch from cursor
    cursor.close() # Close cursor
    conn.close() # Close connection
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['password_hash'], user_data['email'], user_data['is_active'])
    return None

@app.route('/about')
def about():
    return render_template('about.html')

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,)) # Use cursor.execute and %s
        user_data = cursor.fetchone() # Fetch from cursor
        cursor.close() # Close cursor
        conn.close() # Close connection

        if user_data:
            user = User(user_data['id'], user_data['username'], user_data['password_hash'], user_data['email'], user_data['is_active'])
            if user.check_password(password):
                login_user(user)
                flash('Inicio de sesión exitoso.', 'success')
                log_activity(user.id, 'LOGIN', f'User {user.username} logged in.')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
        
        flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'LOGOUT', f'User {current_user.username} logged out.')
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        
        # Check if it's the first user
        cursor.execute('SELECT COUNT(id) FROM users') # Use cursor.execute
        user_count = cursor.fetchone()[0] # Fetch from cursor
        
        hashed_password = generate_password_hash(password)
        
        try:
            cursor.execute('INSERT INTO users (username, password_hash, email, is_active) VALUES (%s, %s, %s, %s) RETURNING id', # Use RETURNING id
                         (username, hashed_password, email, True))
            user_id = cursor.fetchone()[0] # Fetch from cursor

            if user_count == 0:
                # First user becomes Admin
                cursor.execute("SELECT id FROM roles WHERE name = %s", ('Admin',)) # Use cursor.execute and %s
                role_id = cursor.fetchone()['id'] # Fetch from cursor
                role_name = 'Admin'
            else:
                # Subsequent users become Oficinista by default
                cursor.execute("SELECT id FROM roles WHERE name = %s", ('Oficinista',)) # Use cursor.execute and %s
                role_id = cursor.fetchone()['id'] # Fetch from cursor
                role_name = 'Oficinista'
            
            cursor.execute('INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)', (user_id, role_id)) # Use cursor.execute and %s
            
            conn.commit()
            flash(f'Usuario "{username}" registrado exitosamente como {role_name}. Ahora puedes iniciar sesión.', 'success')
            log_activity(user_id, 'REGISTER', f'New user registered: {username}.')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError: # Use psycopg2.IntegrityError
            flash('Error: El nombre de usuario o el email ya existen.', 'danger')
            conn.rollback() # Rollback on error
        finally:
            cursor.close() # Close cursor
            conn.close() # Close connection

    return render_template('register.html')

# --- User Management (Admin Only) ---
@app.route('/users')
@permission_required('view_users')
def list_users():
    # TODO: Implement role-based access control here (only Admin can view)
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    users = cursor.execute('SELECT u.*, STRING_AGG(r.name, ', ') as roles FROM users u LEFT JOIN user_roles ur ON u.id = ur.user_id LEFT JOIN roles r ON ur.role_id = r.id GROUP BY u.id ORDER BY u.username').fetchall() # Use STRING_AGG for PostgreSQL
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('users/list.html', users=users)

# --- Freelancer Management ---
@app.route('/freelancers')
@permission_required('view_freelancers')
def list_freelancers():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    freelancers = cursor.execute(
        "SELECT u.*, STRING_AGG(r.name, ', ') as roles, fd.category, fd.specialty, fd.phone, fd.whatsapp, fd.web " # Use STRING_AGG
        "FROM users u "
        "JOIN user_roles ur ON u.id = ur.user_id "
        "JOIN roles r ON ur.role_id = r.id "
        "LEFT JOIN freelancer_details fd ON u.id = fd.id " # Join with freelancer_details
        "WHERE r.name = 'Autonomo' "
        "GROUP BY u.id ORDER BY u.username"
    ).fetchall() # Fetch from cursor
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('freelancers/list.html', freelancers=freelancers)

@app.route('/users/add', methods=['GET', 'POST'])
@permission_required('manage_users')
def add_user():
    # TODO: Implement role-based access control here (only Admin can add)
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    roles = cursor.execute('SELECT * FROM roles').fetchall() # Use cursor.execute
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role_ids = request.form.getlist('roles') # Get list of selected role IDs

        hashed_password = generate_password_hash(password)
        try:
            # Re-open connection to perform transaction
            # conn_post = get_db_connection() # No need to re-open, use existing conn
            cursor_post = conn.cursor() # Get a new cursor for transaction
            cursor_post.execute('INSERT INTO users (username, password_hash, email, is_active) VALUES (%s, %s, %s, %s) RETURNING id', # Use RETURNING id
                         (username, hashed_password, email, True))
            user_id = cursor_post.fetchone()[0] # Fetch from cursor
            
            for role_id in role_ids:
                cursor_post.execute('INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)', (user_id, role_id)) # Use %s
            
            conn.commit() # Commit on connection
            flash(f'Usuario "{username}" agregado exitosamente!', 'success')
            log_activity(current_user.id, 'ADD_USER', f'User {current_user.username} added new user: {username} (ID: {user_id}).')
            return redirect(url_for('list_users'))
        except psycopg2.IntegrityError: # Use psycopg2.IntegrityError
            flash('Error: El nombre de usuario o el email ya existen.', 'danger')
            conn.rollback() # Rollback on error
        finally:
            cursor_post.close() # Close cursor
            conn.close() # Close connection
    
    # Close the initial connection if it's a GET request
    cursor.close() # Close initial cursor
    conn.close() # Close initial connection
    return render_template('users/form.html', title="Agregar Usuario", user={}, roles=roles)

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@permission_required('manage_users')
def edit_user(user_id):
    # TODO: Implement role-based access control here (only Admin can edit)
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    user = cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,)).fetchone() # Use cursor.execute and %s
    user_roles_data = cursor.execute('SELECT role_id FROM user_roles WHERE user_id = %s', (user_id,)).fetchall() # Use cursor.execute and %s
    user_role_ids = [row['role_id'] for row in user_roles_data]
    roles = cursor.execute('SELECT * FROM roles').fetchall() # Use cursor.execute
    cursor.close() # Close cursor
    conn.close() # Close connection

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        new_password = request.form['password']
        role_ids = request.form.getlist('roles')

        hashed_password = user['password_hash']
        if new_password: # Only update password if a new one is provided
            hashed_password = generate_password_hash(new_password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor() # Get a cursor
            cursor.execute('UPDATE users SET username=%s, password_hash=%s, email=%s WHERE id=%s', # Use %s
                         (username, hashed_password, email, user_id))
            
            # Update user roles
            cursor.execute('DELETE FROM user_roles WHERE user_id = %s', (user_id,)) # Use %s
            for role_id in role_ids:
                cursor.execute('INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)', (user_id, role_id)) # Use %s
            
            conn.commit()
            flash(f'Usuario "{username}" actualizado exitosamente!', 'success')
            log_activity(current_user.id, 'EDIT_USER', f'User {current_user.username} edited user: {username} (ID: {user_id}).')
            return redirect(url_for('list_users'))
        except psycopg2.IntegrityError: # Use psycopg2.IntegrityError
            flash('Error: El nombre de usuario o el email ya existen.', 'danger')
            conn.rollback() # Rollback on error
        finally:
            cursor.close() # Close cursor
            conn.close() # Close connection
    
    return render_template('users/form.html', title="Editar Usuario", user=user, roles=roles, user_role_ids=user_role_ids)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@permission_required('manage_users')
def delete_user(user_id):
    # TODO: Implement role-based access control here (only Admin can delete)
    if current_user.id == user_id:
        flash('No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('list_users'))

    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,)) # Use cursor.execute and %s
    conn.commit()
    cursor.close() # Close cursor
    conn.close() # Close connection
    flash('Usuario eliminado exitosamente.', 'success')
    log_activity(current_user.id, 'DELETE_USER', f'User {current_user.username} deleted user with ID: {user_id}.')
    return redirect(url_for('list_users'))


# --- API Endpoint for Calendar ---
@app.route('/api/trabajos')
@login_required
def api_trabajos():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    trabajos = cursor.execute(
        "SELECT t.id, t.titulo, t.fecha_visita, t.estado, c.nombre as client_nombre, u.username as autonomo_nombre "
        "FROM trabajos t "
        "JOIN clients c ON t.client_id = c.id "
        "LEFT JOIN users u ON t.autonomo_id = u.id"
    ).fetchall() # Fetch from cursor
    cursor.close() # Close cursor
    conn.close() # Close connection
    
    events = []
    for trabajo in trabajos:
        title = f"({trabajo['client_nombre']}) {trabajo['titulo']}"
        if trabajo['autonomo_nombre']:
            title = f"[{trabajo['autonomo_nombre']}] " + title
        
        events.append({
            'id': trabajo['id'],
            'title': title,
            'start': trabajo['fecha_visita'],
            'allDay': True,
            'className': f"status-{trabajo['estado'].lower().replace(' ', '-')}"
        })
    return jsonify(events)

# --- API Endpoint for Material Autocomplete ---
@app.route('/api/materials_autocomplete')
@login_required
def materials_autocomplete():
    query = request.args.get('q', '').lower()
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    materials = cursor.execute('SELECT name FROM materials WHERE LOWER(name) LIKE %s ORDER BY name LIMIT 10', ('%' + query + '%',)).fetchall() # Use cursor.execute and %s
    cursor.close() # Close cursor
    conn.close() # Close connection
    material_names = [material['name'] for material in materials]
    return jsonify(material_names)

# --- Dashboards & Lists ---
@app.route('/')
@login_required
def dashboard():
    conn = get_db_connection()
    if conn is None:
        flash('Error: No se pudo conectar a la base de datos.', 'danger')
        return render_template('dashboard.html', stats={}, upcoming_trabajos=[], overdue_trabajos=[], today_workload=0, tomorrow_workload=0, unread_notifications=[], assigned_tasks=[])

    cursor = conn.cursor()
    try:
        # Fetch stats
        cursor.execute("SELECT estado, COUNT(id) as count FROM trabajos GROUP BY estado")
        stats = cursor.fetchall()

        # Fetch upcoming jobs
        cursor.execute(
            "SELECT t.*, c.nombre as client_nombre, u.username as autonomo_nombre "
            "FROM trabajos t "
            "JOIN clients c ON t.client_id = c.id "
            "LEFT JOIN users u ON t.autonomo_id = u.id "
            "WHERE t.fecha_visita::date >= date(NOW()) ORDER BY t.fecha_visita ASC LIMIT 5"
        )
        upcoming_trabajos = cursor.fetchall()

        # Fetch overdue jobs
        cursor.execute(
            "SELECT t.*, c.nombre as client_nombre, u.username as autonomo_nombre "
            "FROM trabajos t "
            "JOIN clients c ON t.client_id = c.id "
            "LEFT JOIN users u ON t.autonomo_id = u.id "
            "WHERE t.fecha_visita::date < date(NOW()) AND t.estado != 'Finalizado' ORDER BY t.fecha_visita DESC"
        )
        overdue_trabajos = cursor.fetchall()

        # Fetch workload for today
        cursor.execute("SELECT COUNT(id) FROM trabajos WHERE fecha_visita::date = date(NOW())")
        today_workload_count = cursor.fetchone()[0]

        # Fetch workload for tomorrow
        cursor.execute("SELECT COUNT(id) FROM trabajos WHERE fecha_visita = date(NOW() + INTERVAL '1 day')")
        tomorrow_workload_count = cursor.fetchone()[0]

        # Generate and fetch notifications
        generate_notifications_for_user(current_user.id)
        
        unread_notifications = []
        if current_user.is_authenticated:
            cursor.execute(
                "SELECT * FROM notifications WHERE user_id = %s AND is_read = FALSE AND (snooze_until IS NULL OR snooze_until <= NOW()) ORDER BY timestamp DESC LIMIT 5",
                (current_user.id,)
            )
            unread_notifications = cursor.fetchall()

        # Fetch assigned tasks for 'Autonomo'
        assigned_tasks = []
        cursor.execute("SELECT r.name FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = %s", (current_user.id,))
        user_roles = cursor.fetchall()
        role_names = [role['name'] for role in user_roles]

        if 'Autonomo' in role_names:
            cursor.execute(
                "SELECT t.id, t.titulo, t.descripcion, t.estado, t.fecha_limite, tr.titulo as trabajo_titulo FROM tareas t "
                "JOIN trabajos tr ON t.trabajo_id = tr.id "
                "WHERE t.autonomo_id = %s AND t.estado != 'Completada' ORDER BY t.fecha_limite ASC",
                (current_user.id,)
            )
            assigned_tasks = cursor.fetchall()

    except (psycopg2.Error, sqlite3.Error) as e:
        flash(f'Error de base de datos: {e}', 'danger')
        # Return empty data to avoid further errors in the template
        stats = []
        upcoming_trabajos = []
        overdue_trabajos = []
        today_workload_count = 0
        tomorrow_workload_count = 0
        unread_notifications = []
        assigned_tasks = []
    finally:
        cursor.close()
        conn.close()

    stats_dict = {stat['estado']: stat['count'] for stat in stats}
    return render_template('dashboard.html', stats=stats_dict, upcoming_trabajos=upcoming_trabajos, overdue_trabajos=overdue_trabajos, today_workload=today_workload_count, tomorrow_workload=tomorrow_workload_count, unread_notifications=unread_notifications, assigned_tasks=assigned_tasks)

# --- Financial Reports ---
@app.route('/reports/financial')
@permission_required('view_financial_reports')
def financial_reports():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    # Fetch all jobs with their financial data
    trabajos = cursor.execute(
        "SELECT t.id, t.titulo, t.presupuesto, t.vat_rate, t.costo_total_materiales, t.costo_total_mano_obra, t.actual_cost_materials, t.actual_cost_labor, c.nombre as client_nombre "
        "FROM trabajos t JOIN clients c ON t.client_id = c.id"
    ).fetchall() # Fetch from cursor

    # Calculate totals
    total_presupuesto = sum(t['presupuesto'] for t in trabajos)
    
    # Use actual costs if available, otherwise estimated costs
    total_costo_materiales = sum(t['actual_cost_materials'] if t['actual_cost_materials'] is not None else t['costo_total_materiales'] for t in trabajos)
    total_costo_mano_obra = sum(t['actual_cost_labor'] if t['actual_cost_labor'] is not None else t['costo_total_mano_obra'] for t in trabajos)
    
    total_gastos = total_costo_materiales + total_costo_mano_obra
    total_beneficio_bruto = total_presupuesto - total_gastos

    # Calculate VAT for income (presupuesto)
    total_iva_ingresos = sum(t['presupuesto'] * (t['vat_rate'] / 100) for t in trabajos)

    # Calculate VAT for expenses
    # Need to fetch all gastos to calculate their VAT
    gastos = cursor.execute('SELECT monto, vat_rate FROM gastos').fetchall() # Use cursor.execute
    total_iva_gastos = sum(g['monto'] * (g['vat_rate'] / 100) for g in gastos)

    cursor.close() # Close cursor
    conn.close() # Close connection

    return render_template(
        'reports/financial.html',
        trabajos=trabajos,
        total_presupuesto=total_presupuesto,
        total_costo_materiales=total_costo_materiales,
        total_costo_mano_obra=total_costo_mano_obra,
        total_gastos=total_gastos,
        total_beneficio_bruto=total_beneficio_bruto,
        total_iva_ingresos=total_iva_ingresos,
        total_iva_gastos=total_iva_gastos,
        total_iva_neto=total_iva_ingresos - total_iva_gastos
    )

# --- Notifications Management ---
@app.route('/notifications')
@permission_required('manage_notifications')
def list_notifications():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    notifications = cursor.execute(
        "SELECT * FROM notifications WHERE user_id = %s AND (snooze_until IS NULL OR snooze_until <= %s) ORDER BY timestamp DESC", # Use %s
        (current_user.id, today)
    ).fetchall() # Fetch from cursor
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('notifications/list.html', notifications=notifications)

@app.route('/api/unread_notifications_count')
@login_required
def unread_notifications_count():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    count = cursor.execute('SELECT COUNT(id) FROM notifications WHERE user_id = %s AND is_read = FALSE', (current_user.id,)).fetchone()[0] # Use cursor.execute, %s, and FALSE
    cursor.close() # Close cursor
    conn.close() # Close connection
    return jsonify({'count': count})

@app.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@permission_required('manage_notifications')
def mark_notification_read(notification_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    cursor.execute('UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s', (notification_id, current_user.id)) # Use cursor.execute, %s, and TRUE
    conn.commit()
    cursor.close() # Close cursor
    conn.close() # Close connection
    flash('Notificación marcada como leída.', 'success')
    return redirect(url_for('list_notifications'))

@app.route('/notifications/snooze/<int:notification_id>', methods=['POST'])
@permission_required('manage_notifications')
def snooze_notification(notification_id):
    snooze_duration = request.form.get('duration') # e.g., '1_day', '1_week', 'tomorrow'
    
    if snooze_duration:
        snooze_time = datetime.now()
        if snooze_duration == '1_day':
            snooze_time += timedelta(days=1)
        elif snooze_duration == '3_days':
            snooze_time += timedelta(days=3)
        elif snooze_duration == '1_week':
            snooze_time += timedelta(weeks=1)
        elif snooze_duration == 'tomorrow':
            snooze_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        # Add more options as needed

        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('UPDATE notifications SET snooze_until = %s, is_read = FALSE WHERE id = %s AND user_id = %s', # Use cursor.execute, %s, and FALSE
                     (snooze_time.isoformat(), notification_id, current_user.id))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash('Notificación pospuesta exitosamente.', 'info')
    else:
        flash('Duración de posposición no válida.', 'danger')
        
    return redirect(url_for('list_notifications'))

@app.route('/trabajos')
@login_required
def list_trabajos():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    
    # Base query for all jobs
    query = 'SELECT t.*, c.nombre as client_nombre, u.username as autonomo_nombre, e.username as encargado_nombre FROM trabajos t JOIN clients c ON t.client_id = c.id LEFT JOIN users u ON t.autonomo_id = u.id LEFT JOIN users e ON t.encargado_id = e.id'
    params = []

    # Check user permissions
    if current_user.has_permission('view_all_jobs'):
        # Admin/Oficinista can view all jobs
        query += ' ORDER BY t.id DESC'
    elif current_user.has_permission('view_own_jobs'):
        # Autonomo can view their assigned jobs and unassigned 'Presupuestado' jobs
        query += ' WHERE t.autonomo_id = %s OR (t.autonomo_id IS NULL AND t.estado = \'Presupuestado\') ORDER BY t.id DESC' # Use %s
        params.append(current_user.id)
    else:
        # Default: no access or redirect
        flash('No tienes permiso para ver trabajos.', 'danger')
        return redirect(url_for('dashboard'))

    trabajos = cursor.execute(query, params).fetchall() # Use cursor.execute
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('trabajos/list.html', trabajos=trabajos)


# --- Client Management ---
@app.route('/clients')
@login_required
def list_clients():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    clients = cursor.execute('SELECT * FROM clients ORDER BY nombre').fetchall() # Use cursor.execute
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('clients/list.html', clients=clients)

@app.route('/clients/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        nombre = request.form['nombre']
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('INSERT INTO clients (nombre, direccion, telefono, whatsapp, email) VALUES (%s, %s, %s, %s, %s)', # Use %s
                     (nombre, request.form['direccion'], request.form['telefono'], request.form['whatsapp'], request.form['email']))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Cliente "{nombre}" agregado exitosamente!', 'success')
        log_activity(current_user.id, 'ADD_CLIENT', f'User {current_user.username} added new client: {nombre}.')
        return redirect(url_for('list_clients'))
    return render_template('clients/form.html', title="Agregar Cliente", client={})

@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    client = cursor.execute('SELECT * FROM clients WHERE id = %s', (client_id,)).fetchone() # Use cursor.execute and %s
    cursor.close() # Close cursor
    conn.close() # Close connection
    if request.method == 'POST':
        nombre = request.form['nombre']
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('UPDATE clients SET nombre=%s, direccion=%s, telefono=%s, whatsapp=%s, email=%s WHERE id=%s', # Use %s
                     (nombre, request.form['direccion'], request.form['telefono'], request.form['whatsapp'], request.form['email'], client_id))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Cliente "{nombre}" actualizado exitosamente!', 'success')
        log_activity(current_user.id, 'EDIT_CLIENT', f'User {current_user.username} edited client: {nombre} (ID: {client_id}).')
        return redirect(url_for('list_clients'))
    return render_template('clients/form.html', title="Editar Cliente", client=client)

@app.route('/clients/delete/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    cursor.execute('DELETE FROM clients WHERE id = %s', (client_id,)) # Use cursor.execute and %s
    conn.commit()
    cursor.close() # Close cursor
    conn.close() # Close connection
    flash('Cliente eliminado exitosamente.', 'success')
    log_activity(current_user.id, 'DELETE_CLIENT', f'User {current_user.username} deleted client with ID: {client_id}.')
    return redirect(url_for('list_clients'))

# --- Proveedor Management ---
@app.route('/proveedores')
@permission_required('view_proveedores')
def list_proveedores():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    proveedores = cursor.execute('SELECT * FROM proveedores ORDER BY nombre').fetchall() # Use cursor.execute
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('proveedores/list.html', proveedores=proveedores)

@app.route('/proveedores/add', methods=['GET', 'POST'])
@permission_required('manage_proveedores')
def add_proveedor():
    if request.method == 'POST':
        nombre = request.form['nombre']
        contacto = request.form['contacto']
        telefono = request.form['telefono']
        email = request.form['email']
        direccion = request.form['direccion']
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('INSERT INTO proveedores (nombre, contacto, telefono, email, direccion) VALUES (%s, %s, %s, %s, %s)', # Use %s
                     (nombre, contacto, telefono, email, direccion))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Proveedor "{nombre}" agregado exitosamente!', 'success')
        log_activity(current_user.id, 'ADD_PROVEEDOR', f'User {current_user.username} added new proveedor: {nombre}.')
        return redirect(url_for('list_proveedores'))
    return render_template('proveedores/form.html', title="Agregar Proveedor", proveedor={})

@app.route('/proveedores/edit/<int:proveedor_id>', methods=['GET', 'POST'])
@permission_required('manage_proveedores')
def edit_proveedor(proveedor_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    proveedor = cursor.execute('SELECT * FROM proveedores WHERE id = %s', (proveedor_id,)).fetchone() # Use cursor.execute and %s
    cursor.close() # Close cursor
    conn.close() # Close connection
    if request.method == 'POST':
        nombre = request.form['nombre']
        contacto = request.form['contacto']
        telefono = request.form['telefono']
        email = request.form['email']
        direccion = request.form['direccion']
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('UPDATE proveedores SET nombre=%s, contacto=%s, telefono=%s, email=%s, direccion=%s WHERE id=%s', # Use %s
                     (nombre, contacto, telefono, email, direccion, proveedor_id))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Proveedor "{nombre}" actualizado exitosamente!', 'success')
        log_activity(current_user.id, 'EDIT_PROVEEDOR', f'User {current_user.username} edited proveedor: {nombre} (ID: {proveedor_id}).')
        return redirect(url_for('list_proveedores'))
    return render_template('proveedores/form.html', title="Editar Proveedor", proveedor=proveedor)

@app.route('/proveedores/delete/<int:proveedor_id>', methods=['POST'])
@permission_required('manage_proveedores')
def delete_proveedor(proveedor_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    cursor.execute('DELETE FROM proveedores WHERE id = %s', (proveedor_id,)) # Use cursor.execute and %s
    conn.commit()
    cursor.close() # Close cursor
    conn.close() # Close connection
    flash('Proveedor eliminado exitosamente.', 'success')
    log_activity(current_user.id, 'DELETE_PROVEEDOR', f'User {current_user.username} deleted proveedor with ID: {proveedor_id}.')
    return redirect(url_for('list_proveedores'))

# --- Service Management ---
@app.route('/services')
@login_required
def list_services():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    services = cursor.execute('SELECT * FROM services ORDER BY name').fetchall() # Use cursor.execute
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('services/list.html', services=services)

@app.route('/services/add', methods=['GET', 'POST'])
@login_required
def add_service():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('INSERT INTO services (name, description, price, category) VALUES (%s, %s, %s, %s)', # Use %s
                     (name, description, price, category))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Servicio "{name}" agregado exitosamente!', 'success')
        log_activity(current_user.id, 'ADD_SERVICE', f'User {current_user.username} added new service: {name}.')
        return redirect(url_for('list_services'))
    return render_template('services/form.html', title="Agregar Servicio", service={})

@app.route('/services/edit/<int:service_id>', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    service = cursor.execute('SELECT * FROM services WHERE id = %s', (service_id,)).fetchone() # Use cursor.execute and %s
    cursor.close() # Close cursor
    conn.close() # Close connection
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('UPDATE services SET name=%s, description=%s, price=%s, category=%s, recommended_price=%s, last_sold_price=%s WHERE id=%s', # Use %s
                     (name, description, price, category, recommended_price, last_sold_price, service_id))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Servicio "{name}" actualizado exitosamente!', 'success')
        log_activity(current_user.id, 'EDIT_SERVICE', f'User {current_user.username} edited service: {name} (ID: {service_id}).')
        return redirect(url_for('list_services'))
    return render_template('services/form.html', title="Editar Servicio", service=service)

@app.route('/services/delete/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    cursor.execute('DELETE FROM services WHERE id = %s', (service_id,)) # Use cursor.execute and %s
    conn.commit()
    cursor.close() # Close cursor
    conn.close() # Close connection
    flash('Servicio eliminado exitosamente.', 'success')
    log_activity(current_user.id, 'DELETE_SERVICE', f'User {current_user.username} deleted service with ID: {service_id}.')
    return redirect(url_for('list_services'))

# --- Material Management ---
@app.route('/materials')
@permission_required('view_materials')
def list_materials():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    materials = cursor.execute('SELECT * FROM materials ORDER BY name').fetchall() # Use cursor.execute
    cursor.close() # Close cursor
    conn.close() # Close connection
    return render_template('materials/list.html', materials=materials)

@app.route('/materials/add', methods=['GET', 'POST'])
@permission_required('manage_materials')
def add_material():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        unit_price = request.form['unit_price']
        min_stock_level = request.form['min_stock_level']
        unit_of_measure = request.form['unit_of_measure'] # New field
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('INSERT INTO materials (name, description, unit_price, min_stock_level, unit_of_measure) VALUES (%s, %s, %s, %s, %s)', # Use %s
                     (name, description, unit_price, min_stock_level, unit_of_measure)) # Updated
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Material "{name}" agregado exitosamente!', 'success')
        log_activity(current_user.id, 'ADD_MATERIAL', f'User {current_user.username} added new material: {name}.')
        return redirect(url_for('list_materials'))
    return render_template('materials/form.html', title="Agregar Material", material={})

@app.route('/materials/edit/<int:material_id>', methods=['GET', 'POST'])
@permission_required('manage_materials')
def edit_material(material_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    material = cursor.execute('SELECT * FROM materials WHERE id = %s', (material_id,)).fetchone() # Use cursor.execute and %s
    cursor.close() # Close cursor
    conn.close() # Close connection
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        unit_price = request.form['unit_price']
        min_stock_level = request.form['min_stock_level']
        unit_of_measure = request.form['unit_of_measure'] # New field
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor
        cursor.execute('UPDATE materials SET name=%s, description=%s, unit_price=%s, min_stock_level=%s, unit_of_measure=%s, recommended_price=%s, last_sold_price=%s WHERE id=%s', # Use %s
                     (name, description, unit_price, min_stock_level, unit_of_measure, recommended_price, last_sold_price, material_id))
        conn.commit()
        cursor.close() # Close cursor
        conn.close() # Close connection
        flash(f'Material "{name}" actualizado exitosamente!', 'success')
        log_activity(current_user.id, 'EDIT_MATERIAL', f'User {current_user.username} edited material: {name} (ID: {material_id}).')
        return redirect(url_for('list_materials'))
    return render_template('materials/form.html', title="Editar Material", material=material)

@app.route('/materials/delete/<int:material_id>', methods=['POST'])
@permission_required('manage_materials')
def delete_material(material_id):
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    cursor.execute('DELETE FROM materials WHERE id = %s', (material_id,)) # Use cursor.execute and %s
    conn.commit()
    cursor.close() # Close cursor
    conn.close() # Close connection
    flash('Material eliminado exitosamente.', 'success')
    log_activity(current_user.id, 'DELETE_MATERIAL', f'User {current_user.username} deleted material with ID: {material_id}.')
    return redirect(url_for('list_materials'))


# --- Stock Movement Management ---
@app.route('/stock_movements/add', methods=['GET', 'POST'])
@login_required
def add_stock_movement():
    conn = get_db_connection()
    cursor = conn.cursor() # Get a cursor
    materials = cursor.execute('SELECT id, name FROM materials ORDER BY name').fetchall() # Use cursor.execute
    
    if request.method == 'POST':
        material_id = request.form['material_id']
        type = request.form['type']
        quantity = float(request.form['quantity'])
        notes = request.form['notes']
        movement_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Re-open connection for transaction
        # conn_post = get_db_connection() # No need to re-open, use existing conn
        cursor_post = conn.cursor() # Get a new cursor for transaction
        try:
            cursor_post.execute('INSERT INTO stock_movements (material_id, type, quantity, movement_date, notes) VALUES (%s, %s, %s, %s, %s)', # Use %s
                         (material_id, type, quantity, movement_date, notes))
            
            if type == 'IN':
                cursor_post.execute('UPDATE materials SET current_stock = current_stock + %s WHERE id = %s', (quantity, material_id)) # Use %s
            elif type == 'OUT':
                cursor_post.execute('UPDATE materials SET current_stock = current_stock - %s WHERE id = %s', (quantity, material_id)) # Use %s
            
            conn.commit()
            flash('Movimiento de stock registrado exitosamente.', 'success')
            log_activity(current_user.id, 'ADD_STOCK_MOVEMENT', f'User {current_user.username} recorded a stock movement for material ID: {material_id} (Type: {type}, Quantity: {quantity}).')
            return redirect(url_for('list_materials'))
        finally:
            cursor_post.close() # Close cursor
            conn.close() # Close connection

    cursor.close() # Close initial cursor
    conn.close() # Close initial connection
    return render_template('stock_movements/form.html', title="Registrar Movimiento de Stock", materials=materials)

# --- Job Management ---
@app.route('/trabajos/add', methods=['GET', 'POST'])
@permission_required('manage_all_jobs')
def add_trabajo():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT id, nombre FROM clients ORDER BY nombre')
        clients = cursor.fetchall()
        cursor.execute("SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'Autonomo' ORDER BY u.username")
        autonomos = cursor.fetchall()
    
    candidate_autonomos = [] 

    if request.method == 'POST':
        autonomo_id = request.form.get('autonomo_id')
        if not autonomo_id:
            autonomo_id = None

        assigned_autonomo = None
        proposed_autonomo = None
        approval_status = 'Pending'

        if current_user.has_permission('manage_all_jobs'):
            assigned_autonomo = autonomo_id
            approval_status = 'Approved'
        else:
            proposed_autonomo = autonomo_id
            assigned_autonomo = None

        vat_rate = float(request.form['vat_rate'])
        encargado_id = None
        if current_user.has_permission('manage_all_jobs'):
            encargado_id = current_user.id

        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO trabajos (client_id, autonomo_id, proposed_autonomo_id, approval_status, encargado_id, titulo, descripcion, estado, presupuesto, vat_rate, fecha_visita, costo_total_materiales, costo_total_mano_obra) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (request.form['client_id'], assigned_autonomo, proposed_autonomo, approval_status, encargado_id, request.form['titulo'], request.form['descripcion'], request.form['estado'], request.form['presupuesto'], vat_rate, request.form['fecha_visita'], 0, 0))
        conn.commit()
        conn.close()
        flash('Trabajo agregado exitosamente!', 'success')
        log_activity(current_user.id, 'ADD_JOB', f'User {current_user.username} added new job: {request.form["titulo"]} for client ID: {request.form["client_id"]}.')
        return redirect(url_for('list_trabajos'))
    
    conn.close()
    return render_template('trabajos/form.html', title="Agregar Trabajo", clients=clients, autonomos=autonomos, trabajo={}, candidate_autonomos=candidate_autonomos)

# --- Task Management ---
@app.route('/trabajos/<int:trabajo_id>/tareas/add', methods=['GET', 'POST'])
@login_required
def add_tarea(trabajo_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT id, titulo, autonomo_id FROM trabajos WHERE id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()

    # Permission check: Admin/Oficinista can manage all tasks, Autonomo can only manage tasks for their own jobs
    if not current_user.has_permission('manage_all_tasks'):
        if not (current_user.has_permission('manage_own_tasks') and trabajo and trabajo['autonomo_id'] == current_user.id):
            flash('No tienes permiso para añadir tareas a este trabajo.', 'danger')
            conn.close()
            return redirect(url_for('dashboard'))

    with conn.cursor() as cursor:
        cursor.execute('SELECT id, titulo FROM trabajos WHERE id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()
        cursor.execute("SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'Autonomo' ORDER BY u.username")
        autonomos = cursor.fetchall()

    if trabajo is None:
        flash('Trabajo no encontrado.', 'danger')
        conn.close()
        return redirect(url_for('list_trabajos'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        estado = request.form['estado']
        fecha_limite = request.form['fecha_limite'] if request.form['fecha_limite'] else None
        autonomo_id = request.form.get('autonomo_id')
        if not autonomo_id:
            autonomo_id = None
        
        # New payment fields
        metodo_pago = request.form.get('metodo_pago')
        estado_pago = request.form.get('estado_pago')
        monto_abonado = float(request.form.get('monto_abonado', 0.0))
        fecha_pago = request.form.get('fecha_pago') if request.form.get('fecha_pago') else None

        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO tareas (trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (trabajo_id, titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago)
            )
        conn.commit()
        conn.close()
        flash('Tarea agregada exitosamente!', 'success')
        log_activity(current_user.id, 'ADD_TASK', f'User {current_user.username} added new task: {titulo} to job ID: {trabajo_id}.')
        return redirect(url_for('edit_trabajo', trabajo_id=trabajo_id))

    conn.close()
    estados_tarea = ['Pendiente', 'En Progreso', 'Completada', 'Bloqueada']
    metodos_pago = ['Efectivo', 'Tarjeta', 'Transferencia', 'Pendiente']
    estados_pago = ['Abonado', 'Pendiente', 'Parcialmente Abonado']
    return render_template('tareas/form.html', title="Agregar Tarea", trabajo=trabajo, autonomos=autonomos, estados_tarea=estados_tarea, tarea={}, metodos_pago=metodos_pago, estados_pago=estados_pago)

@app.route('/trabajos/edit/<int:trabajo_id>', methods=['GET', 'POST'])
@login_required
def edit_trabajo(trabajo_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT t.*, u.username as encargado_nombre FROM trabajos t LEFT JOIN users u ON t.encargado_id = u.id WHERE t.id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()
    
        # Fetch potential freelancer candidates based on client history
        candidate_autonomos = []
        if trabajo and trabajo['client_id']:
            cursor.execute(
                "SELECT DISTINCT u.id, u.username FROM users u "
                "JOIN trabajos t ON u.id = t.autonomo_id "
                "WHERE t.client_id = %s AND u.id IS NOT NULL",
                (trabajo['client_id'],)
            )
            candidate_autonomos = cursor.fetchall()

    # Permission check: Admin/Oficinista can manage all jobs, Autonomo can only manage their own
    if not current_user.has_permission('manage_all_jobs'):
        if not (current_user.has_permission('manage_own_jobs') and trabajo and trabajo['autonomo_id'] == current_user.id):
            flash('No tienes permiso para editar este trabajo.', 'danger')
            conn.close()
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        autonomo_id = request.form.get('autonomo_id')
        if not autonomo_id: # Handle the "unassigned" case
            autonomo_id = None

        vat_rate = float(request.form['vat_rate'])
        # Determine if user can directly assign or only propose
        assigned_autonomo = None
        proposed_autonomo = None
        approval_status = trabajo['approval_status'] # Keep existing status by default

        if current_user.has_permission('manage_all_jobs'): # Admin/Oficinista can directly assign
            assigned_autonomo = autonomo_id
            approval_status = 'Approved'
        else: # Other roles can only propose
            proposed_autonomo = autonomo_id
            assigned_autonomo = trabajo['autonomo_id'] # Keep existing assigned until approved

        # Determine encargado_id based on current_user's role or existing value
        encargado_id = trabajo['encargado_id'] # Keep existing encargado
        if current_user.has_permission('manage_all_jobs') and not encargado_id: # Admin/Oficinista can set if not already set
            encargado_id = current_user.id

        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE trabajos SET client_id=%s, autonomo_id=%s, proposed_autonomo_id=%s, approval_status=%s, encargado_id=%s, titulo=%s, descripcion=%s, estado=%s, presupuesto=%s, vat_rate=%s, fecha_visita=%s WHERE id=%s',
                (request.form['client_id'], assigned_autonomo, proposed_autonomo, approval_status, encargado_id, request.form['titulo'], request.form['descripcion'], request.form['estado'], request.form['presupuesto'], vat_rate, request.form['fecha_visita'], trabajo_id))
        # Note: costo_total_materiales and costo_total_mano_obra are updated via add_gasto, not directly here.
        conn.commit()
        conn.close()
        flash('Trabajo actualizado exitosamente!', 'success')
        log_activity(current_user.id, 'EDIT_JOB', f'User {current_user.username} edited job: {request.form["titulo"]} (ID: {trabajo_id}).')
        return redirect(url_for('list_trabajos'))

    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM trabajos WHERE id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()
        cursor.execute('SELECT id, nombre FROM clients ORDER BY nombre')
        clients = cursor.fetchall()
        cursor.execute("SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'Autonomo' ORDER BY u.username")
        autonomos = cursor.fetchall()
        
        # Fetch expenses for this job
        cursor.execute('SELECT * FROM gastos WHERE trabajo_id = %s ORDER BY fecha DESC', (trabajo_id,))
        gastos = cursor.fetchall()

        # Fetch quotes for this job
        cursor.execute(
            "SELECT jq.*, u.username as autonomo_nombre FROM job_quotes jq "
            "JOIN users u ON jq.autonomo_id = u.id "
            "WHERE jq.trabajo_id = %s ORDER BY jq.quote_date DESC",
            (trabajo_id,)
        )
        quotes = cursor.fetchall()

        # Fetch tasks for this job
        cursor.execute(
            "SELECT t.*, u.username as autonomo_nombre FROM tareas t "
            "LEFT JOIN users u ON t.autonomo_id = u.id "
            "WHERE t.trabajo_id = %s ORDER BY t.estado, t.fecha_limite",
            (trabajo_id,)
        )
        tareas = cursor.fetchall()

    conn.close()
    return render_template('trabajos/form.html', title="Editar Trabajo", clients=clients, autonomos=autonomos, trabajo=trabajo, gastos=gastos, tareas=tareas, candidate_autonomos=candidate_autonomos, quotes=quotes)

@app.route('/trabajos/<int:trabajo_id>/tareas/edit/<int:tarea_id>', methods=['GET', 'POST'])
@login_required
def edit_tarea(trabajo_id, tarea_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT id, titulo, autonomo_id FROM trabajos WHERE id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()
        cursor.execute('SELECT * FROM tareas WHERE id = %s AND trabajo_id = %s', (tarea_id, trabajo_id))
        tarea = cursor.fetchone()

    # Permission check: Admin/Oficinista can manage all tasks, Autonomo can only manage their own tasks
    if not current_user.has_permission('manage_all_tasks'):
        if not (current_user.has_permission('manage_own_tasks') and trabajo and trabajo['autonomo_id'] == current_user.id and tarea and tarea['autonomo_id'] == current_user.id):
            flash('No tienes permiso para editar esta tarea.', 'danger')
            conn.close()
            return redirect(url_for('dashboard'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        estado = request.form['estado']
        fecha_limite = request.form['fecha_limite'] if request.form['fecha_limite'] else None
        autonomo_id = request.form.get('autonomo_id')
        if not autonomo_id:
            autonomo_id = None
        
        # New payment fields
        metodo_pago = request.form.get('metodo_pago')
        estado_pago = request.form.get('estado_pago')
        monto_abonado = float(request.form.get('monto_abonado', 0.0))
        fecha_pago = request.form.get('fecha_pago') if request.form.get('fecha_pago') else None

        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE tareas SET titulo=%s, descripcion=%s, estado=%s, fecha_limite=%s, autonomo_id=%s, metodo_pago=%s, estado_pago=%s, monto_abonado=%s, fecha_pago=%s WHERE id=%s AND trabajo_id=%s',
                (titulo, descripcion, estado, fecha_limite, autonomo_id, metodo_pago, estado_pago, monto_abonado, fecha_pago, tarea_id, trabajo_id)
            )
        conn.commit()
        conn.close()
        flash('Tarea actualizada exitosamente!', 'success')
        log_activity(current_user.id, 'EDIT_TASK', f'User {current_user.username} edited task: {titulo} (ID: {tarea_id}) for job ID: {trabajo_id}.')
        return redirect(url_for('edit_trabajo', trabajo_id=trabajo_id))

    with conn.cursor() as cursor:
        cursor.execute('SELECT id, titulo FROM trabajos WHERE id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()
        cursor.execute('SELECT * FROM tareas WHERE id = %s AND trabajo_id = %s', (tarea_id, trabajo_id))
        tarea = cursor.fetchone()
        cursor.execute("SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'Autonomo' ORDER BY u.username")
        autonomos = cursor.fetchall()
    
    conn.close()
    if trabajo is None:
        flash('Trabajo no encontrado.', 'danger')
        return redirect(url_for('list_trabajos'))
    if tarea is None:
        flash('Tarea no encontrada.', 'danger')
        return redirect(url_for('edit_trabajo', trabajo_id=trabajo_id))

    estados_tarea = ['Pendiente', 'En Progreso', 'Completada', 'Bloqueada']
    metodos_pago = ['Efectivo', 'Tarjeta', 'Transferencia', 'Pendiente']
    estados_pago = ['Abonado', 'Pendiente', 'Parcialmente Abonado']
    return render_template('tareas/form.html', title="Editar Tarea", trabajo=trabajo, autonomos=autonomos, estados_tarea=estados_tarea, tarea=tarea, metodos_pago=metodos_pago, estados_pago=estados_pago)

@app.route('/trabajos/delete/<int:trabajo_id>', methods=['POST'])
@permission_required('manage_all_jobs')
def delete_trabajo(trabajo_id):
    pass # Placeholder for function body



@app.route('/trabajos/<int:trabajo_id>/quotes/add', methods=['GET', 'POST'])
@login_required
def add_quote(trabajo_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT * FROM trabajos WHERE id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()
    
        # Permission check: Only assigned freelancer or manager can create quotes for this job
        if not current_user.has_permission('manage_all_jobs'): # Manager can create quotes for any job
            if not (current_user.has_permission('manage_own_jobs') and trabajo and trabajo['autonomo_id'] == current_user.id):
                flash('No tienes permiso para crear un presupuesto para este trabajo.', 'danger')
                conn.close()
                return redirect(url_for('dashboard'))

        cursor.execute('SELECT id, name, unit_price, unit_of_measure, recommended_price, last_sold_price FROM materials ORDER BY name')
        materials = cursor.fetchall()
        cursor.execute('SELECT id, name, price, category, recommended_price, last_sold_price FROM services ORDER BY name')
        services = cursor.fetchall()
    
        # Fetch freelancer's hourly rates
        cursor.execute('SELECT hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate FROM freelancer_details WHERE id = %s', (current_user.id,))
        freelancer_details = cursor.fetchone()
    
    if request.method == 'POST':
        # Get data from form
        material_ids = request.form.getlist('material_id[]')
        material_quantities = request.form.getlist('material_quantity[]')
        material_prices = request.form.getlist('material_price[]')

        service_ids = request.form.getlist('service_id[]')
        service_prices = request.form.getlist('service_price[]')

        hours_normal = float(request.form.get('hours_normal', 0))
        hours_tier2 = float(request.form.get('hours_tier2', 0))
        hours_tier3 = float(request.form.get('hours_tier3', 0))

        client_notes = request.form.get('client_notes', '')
        freelancer_notes = request.form.get('freelancer_notes', '')

        # Calculate totals
        total_materials_cost = 0.0
        for i in range(len(material_ids)):
            try:
                qty = float(material_quantities[i])
                price = float(material_prices[i])
                total_materials_cost += qty * price
            except ValueError:
                pass # Handle invalid input

        total_services_cost = 0.0
        for i in range(len(service_ids)):
            try:
                price = float(service_prices[i])
                total_services_cost += price
            except ValueError:
                pass # Handle invalid input

        # Calculate total labor cost with difficulty surcharge
        difficulty_surcharge = 1 + (freelancer_details['difficulty_surcharge_rate'] * trabajo['job_difficulty_rating'] / 100)
        total_labor_cost = ((hours_normal * freelancer_details['hourly_rate_normal']) + \
                           (hours_tier2 * freelancer_details['hourly_rate_tier2']) + \
                           (hours_tier3 * freelancer_details['hourly_rate_tier3'])) * difficulty_surcharge
        
        subtotal = total_materials_cost + total_services_cost + total_labor_cost
        vat_rate = trabajo['vat_rate'] # Use job's VAT rate
        total_quote_amount = subtotal * (1 + (vat_rate / 100))

        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO job_quotes (trabajo_id, autonomo_id, quote_date, status, total_materials_cost, total_labor_cost, total_services_cost, total_quote_amount, vat_rate, client_notes, freelancer_notes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (trabajo_id, current_user.id, datetime.now().isoformat(), 'Draft', total_materials_cost, total_labor_cost, total_services_cost, total_quote_amount, vat_rate, client_notes, freelancer_notes)
            )
        conn.commit()
        conn.close()
        flash('Presupuesto creado exitosamente!', 'success')
        log_activity(current_user.id, 'CREATE_QUOTE', f'User {current_user.username} created a quote for job ID: {trabajo_id}.')
        return redirect(url_for('edit_trabajo', trabajo_id=trabajo_id))
    
    conn.close()
    return render_template('quotes/form.html', title="Crear Presupuesto", trabajo=trabajo, materials=materials, services=services, freelancer_details=freelancer_details)


@app.route('/trabajos/approve/<int:trabajo_id>', methods=['POST'])
@permission_required('manage_all_jobs')
def approve_job(trabajo_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('SELECT proposed_autonomo_id FROM trabajos WHERE id = %s', (trabajo_id,))
        trabajo = cursor.fetchone()
    
        if trabajo and trabajo['proposed_autonomo_id']:
            cursor.execute('UPDATE trabajos SET autonomo_id = %s, proposed_autonomo_id = NULL, approval_status = \'Approved\' WHERE id = %s',
                         (trabajo['proposed_autonomo_id'], trabajo_id))
            conn.commit()
            flash('Trabajo aprobado y autónomo asignado exitosamente.', 'success')
        else:
            flash('No se pudo aprobar el trabajo o no hay autónomo propuesto.', 'danger')
    
    conn.close()
    return redirect(url_for('job_approval_list'))

@app.route('/trabajos/reject/<int:trabajo_id>', methods=['POST'])
@permission_required('manage_all_jobs')
def reject_job(trabajo_id):
    conn = get_db_connection()
    conn.execute('UPDATE trabajos SET proposed_autonomo_id = NULL, approval_status = \'Rejected\' WHERE id = ?', (trabajo_id,))
    conn.commit()
    conn.close()
    flash('Trabajo rechazado. El autónomo propuesto ha sido desvinculado.', 'info')
    return redirect(url_for('job_approval_list'))


@app.route('/tareas/delete/<int:tarea_id>', methods=['POST'])
@login_required
def delete_tarea(tarea_id):
    conn = get_db_connection()
    tarea = conn.execute('SELECT trabajo_id, titulo, autonomo_id FROM tareas WHERE id = ?', (tarea_id,)).fetchone()
    conn.close() # Close connection early for permission check

    # Permission check: Admin/Oficinista can manage all tasks, Autonomo can only manage their own tasks
    if not current_user.has_permission('manage_all_tasks'):
        if not (current_user.has_permission('manage_own_tasks') and tarea and tarea['autonomo_id'] == current_user.id):
            flash('No tienes permiso para eliminar esta tarea.', 'danger')
            return redirect(url_for('dashboard'))

    # Re-open connection for main function logic
    conn = get_db_connection()
    conn = get_db_connection()
    tarea = conn.execute('SELECT trabajo_id, titulo FROM tareas WHERE id = ?', (tarea_id,)).fetchone()

    if tarea:
        trabajo_id = tarea['trabajo_id']
        titulo_tarea = tarea['titulo']
        conn.execute('DELETE FROM tareas WHERE id = ?', (tarea_id,))
        conn.commit()
        conn.close()
        flash('Tarea eliminada exitosamente.', 'success')
        log_activity(current_user.id, 'DELETE_TASK', f'User {current_user.username} deleted task: {titulo_tarea} (ID: {tarea_id}) from job ID: {trabajo_id}.')
        return redirect(url_for('edit_trabajo', trabajo_id=trabajo_id))
    else:
        conn.close()
        flash('Tarea no encontrada.', 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard or a more appropriate page

# --- Gastos Management ---
@app.route('/trabajos/<int:trabajo_id>/gastos/add', methods=['GET', 'POST'])
@login_required
def add_gasto(trabajo_id):
    conn = get_db_connection()
    trabajo = conn.execute('SELECT id, titulo FROM trabajos WHERE id = ?', (trabajo_id,)).fetchone()
    
    # Fetch materials and services for the form
    materials = conn.execute('SELECT id, name FROM materials ORDER BY name').fetchall()
    services = conn.execute('SELECT id, name FROM services ORDER BY name').fetchall()
    autonomos = conn.execute("SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'Autonomo' ORDER BY u.username").fetchall()
    
    conn.close()

    if trabajo is None:
        flash('Trabajo no encontrado.', 'danger')
        return redirect(url_for('list_trabajos'))

    if request.method == 'POST':
        descripcion = request.form['descripcion']
        tipo = request.form['tipo']
        monto = float(request.form['monto'])
        fecha = request.form['fecha'] # Assuming YYYY-MM-DD from input type="date"

        vat_rate = float(request.form['vat_rate'])
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO gastos (trabajo_id, descripcion, tipo, monto, vat_rate, fecha) VALUES (?, ?, ?, ?, ?, ?)',
            (trabajo_id, descripcion, tipo, monto, vat_rate, fecha)
        )
        gasto_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Update total costs in trabajos table
        if tipo == 'Material':
            conn.execute('UPDATE trabajos SET costo_total_materiales = costo_total_materiales + ? WHERE id = ?', (monto, trabajo_id))
        elif tipo == 'Mano de Obra':
            conn.execute('UPDATE trabajos SET costo_total_mano_obra = costo_total_mano_obra + ? WHERE id = ?', (monto, trabajo_id))
        # Add other types if needed, or a generic 'otros_costos'

        # Handle installation costs if checkbox is checked
        if 'add_installation_cost' in request.form:
            install_material_id = request.form.get('install_material_id') if request.form.get('install_material_id') else None
            install_service_id = request.form.get('install_service_id') if request.form.get('install_service_id') else None
            install_description = request.form.get('install_description')
            install_cost = float(request.form.get('install_cost', 0.0))
            install_revenue = float(request.form.get('install_revenue', 0.0))
            install_date = request.form.get('install_date') if request.form.get('install_date') else fecha # Default to main expense date
            install_notes = request.form.get('install_notes')

            conn.execute(
                'INSERT INTO job_material_install_costs (job_id, material_id, service_id, description, cost, revenue, date, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (trabajo_id, install_material_id, install_service_id, install_description, install_cost, install_revenue, install_date, install_notes)
            )

        # Handle shared expenses if checkbox is checked
        if 'add_shared_expense' in request.form:
            shared_user_ids = request.form.getlist('shared_user_id[]')
            shared_amounts = request.form.getlist('shared_amount[]')
            shared_billed_to_client = request.form.getlist('shared_billed_to_client[]')
            shared_notes = request.form.getlist('shared_notes[]')

            for i in range(len(shared_user_ids)):
                user_id = shared_user_ids[i]
                amount_shared = float(shared_amounts[i])
                billed_to_client = 1 if 'on' in shared_billed_to_client and i < len(shared_billed_to_client) and shared_billed_to_client[i] == '1' else 0
                notes = shared_notes[i] if i < len(shared_notes) else ''

                if user_id: # Only insert if a user is selected
                    conn.execute(
                        'INSERT INTO shared_expenses (gasto_id, user_id, amount_shared, is_billed_to_client, notes) VALUES (?, ?, ?, ?, ?)',
                        (gasto_id, user_id, amount_shared, billed_to_client, notes)
                    )

        conn.commit()
        conn.close()
        flash('Gasto agregado exitosamente!', 'success')
        log_activity(current_user.id, 'ADD_EXPENSE', f'User {current_user.username} added expense for job ID: {trabajo_id} (Amount: {monto}, Type: {tipo}).')
        # Redirect back to the job's edit page or a new view_job page
        return redirect(url_for('edit_trabajo', trabajo_id=trabajo_id)) # For now, redirect to edit job

    # Predefined types for the dropdown
    tipos_gasto = ['Material', 'Mano de Obra', 'Transporte', 'Comida', 'Otros']
    return render_template('gastos/form.html', title="Agregar Gasto", trabajo=trabajo, tipos_gasto=tipos_gasto, gasto={}, materials=materials, services=services, autonomos=autonomos)

@app.route('/gastos/delete/<int:gasto_id>', methods=['POST'])
@login_required
def delete_gasto(gasto_id):
    conn = get_db_connection()
    gasto = conn.execute('SELECT * FROM gastos WHERE id = ?', (gasto_id,)).fetchone()

    if gasto:
        trabajo_id = gasto['trabajo_id']
        monto = gasto['monto']
        tipo = gasto['tipo']
        vat_rate = gasto['vat_rate']
        
        # Calculate VAT-exclusive amount
        monto_sin_iva = monto / (1 + (vat_rate / 100))

        conn.execute('DELETE FROM gastos WHERE id = ?', (gasto_id,))

        # Update total costs in trabajos table
        if tipo == 'Material':
            conn.execute('UPDATE trabajos SET costo_total_materiales = costo_total_materiales - ? WHERE id = ?', (monto_sin_iva, trabajo_id))
        elif tipo == 'Mano de Obra':
            conn.execute('UPDATE trabajos SET costo_total_mano_obra = costo_total_mano_obra - ? WHERE id = ?', (monto_sin_iva, trabajo_id))

        conn.commit()
        conn.close()
        flash('Gasto eliminado exitosamente.', 'success')
        return redirect(url_for('edit_trabajo', trabajo_id=trabajo_id))
    else:
        conn.close()
        flash('Gasto no encontrado.', 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard or a more appropriate pagege