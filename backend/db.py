# backend/db.py
import os
import sqlite3
import click
import re
import traceback
import sys
from flask import current_app, g
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def get_db():
    if "db" not in g:
        try:
            path = current_app.config["DATABASE"]
            # Ensure the directory for the database file exists
            os.makedirs(os.path.dirname(path), exist_ok=True)
            g.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            # Log the error to console, as dbmod.log_error would call get_db() again
            print(f"ERROR: Could not connect to database in get_db: {e}")
            import traceback
            traceback.print_exc()
            g.db = None # Set g.db to None to avoid repeated attempts
            return None # Return None to indicate failure
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db_func():
    print("--- [START] Database Initialization ---", flush=True)
    db_path = current_app.config["DATABASE"]
    print(f"[INFO] Database path: {db_path}", flush=True)

    if os.path.exists(db_path):
        print("[INFO] Deleting existing database file.", flush=True)
        os.remove(db_path)

    try:
        print("[INFO] Getting database connection.", flush=True)
        db = get_db()
        if db is None:
            print("[FATAL] get_db() returned None. Aborting.", file=sys.stderr, flush=True)
            return

        print("[INFO] Reading schema.sql file.", flush=True)
        with current_app.open_resource("schema.sql") as f:
            schema_sql = f.read().decode("utf-8")
        print(f"[INFO] schema.sql read successfully. Length: {len(schema_sql)}", flush=True)

        print("[INFO] Executing schema script.", flush=True)
        db.executescript(schema_sql)
        print("[INFO] Schema script executed successfully.", flush=True)

        print("[INFO] Seeding roles table.", flush=True)
        roles = [
            ('admin', 'Administrador'),
            ('oficina', 'Personal de Oficina'),
            ('jefe_obra', 'Jefe de Obra'),
            ('tecnico', 'Técnico'),
            ('autonomo', 'Autónomo'),
            ('cliente', 'Cliente')
        ]
        db.executemany("INSERT INTO roles (code, descripcion) VALUES (?, ?)", roles)
        print("[INFO] Roles seeded successfully.", flush=True)

        print("[INFO] Seeding users table.", flush=True)
        admin_password = generate_password_hash('password123')
        users = [
            ('admin', admin_password, 'admin', 'Admin User', 'admin@example.com'),
            ('oficina', admin_password, 'oficina', 'Oficina User', 'oficina@example.com'),
            ('cliente', admin_password, 'cliente', 'Cliente User', 'cliente@example.com'),
            ('autonomo', admin_password, 'autonomo', 'Autonomo User', 'autonomo@example.com')
        ]
        db.executemany("INSERT INTO users (username, password_hash, role, nombre, email) VALUES (?, ?, ?, ?, ?)", users)
        print("[INFO] Users seeded successfully.", flush=True)

        print("[INFO] Seeding user_roles table.", flush=True)
        user_roles = []
        for user_role in ['admin', 'oficina', 'cliente', 'autonomo']:
            cursor = db.execute(f"SELECT id FROM users WHERE username = ?", (user_role,))
            user_row = cursor.fetchone()
            cursor = db.execute(f"SELECT id FROM roles WHERE code = ?", (user_role,))
            role_row = cursor.fetchone()
            if user_row and role_row:
                user_roles.append((user_row['id'], role_row['id']))
        db.executemany("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", user_roles)
        print("[INFO] user_roles seeded successfully.", flush=True)

        print("[INFO] Seeding clientes table.", flush=True)
        db.execute("INSERT INTO clientes (nombre, telefono, email, nif) VALUES (?, ?, ?, ?)", ('Cliente Demo 1', '111222333', 'cliente1@example.com', '12345678A'))
        db.execute("INSERT INTO clientes (nombre, telefono, email, nif, is_ngo) VALUES (?, ?, ?, ?, ?)", ('ONG Ayuda Social', '444555666', 'ong@example.com', 'G12345678', 1))
        print("[INFO] clientes seeded successfully.", flush=True)

        print("[INFO] Seeding direcciones table.", flush=True)
        db.execute("INSERT INTO direcciones (cliente_id, linea1, ciudad, provincia, cp) VALUES (?, ?, ?, ?, ?)", (1, 'Calle Falsa 123', 'Valencia', 'Valencia', '46001'))
        db.execute("INSERT INTO direcciones (cliente_id, linea1, ciudad, provincia, cp) VALUES (?, ?, ?, ?, ?)", (2, 'Avenida Siempre Viva 742', 'Madrid', 'Madrid', '28001'))
        print("[INFO] direcciones seeded successfully.", flush=True)

        print("[INFO] Seeding services table.", flush=True)
        servicios = [
            ('Fontanería General', 'Reparación de tuberías, grifos, desatascos.', 60.00, 'Fontanería'),
            ('Instalación de Sanitarios', 'Instalación de inodoros, lavabos, duchas.', 150.00, 'Fontanería'),
            ('Electricidad Básica', 'Reparación de enchufes, interruptores, puntos de luz.', 55.00, 'Electricidad'),
            ('Instalación de Lámparas', 'Montaje e instalación de todo tipo de lámparas.', 45.00, 'Electricidad'),
            ('Limpieza de Oficinas', 'Servicio de limpieza para oficinas (precio por hora).', 25.00, 'Limpieza'),
            ('Limpieza de Comunidades', 'Limpieza de zonas comunes en comunidades de vecinos.', 90.00, 'Limpieza'),
            ('Mantenimiento General', 'Pequeñas reparaciones de albañilería, pintura, etc.', 50.00, 'Mantenimiento')
        ]
        db.executemany("INSERT INTO services (name, description, price, category) VALUES (?, ?, ?, ?)", servicios)
        print("[INFO] services seeded successfully.", flush=True)

        print("[INFO] Seeding materiales table.", flush=True)
        materiales = [
            ('MAT001', 'Tornillos Estrella 4x40', 'Ferretería', 'caja 100u', 100, 10, 'Almacén A1', 5.50),
            ('MAT002', 'Cable 2.5mm Negro', 'Electricidad', 'metro', 50, 5, 'Furgoneta 1', 0.75),
            ('PLOM01', 'Cinta de teflón', 'Fontanería', 'rollo', 30, 10, 'Almacén B2', 1.20),
            ('PINT01', 'Rodillo de espuma', 'Pintura', 'unidad', 15, 5, 'Almacén A1', 3.50)
        ]
        db.executemany("INSERT INTO materiales (sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", materiales)
        print("[INFO] materiales seeded successfully.", flush=True)

        print("[INFO] Seeding tickets table.", flush=True)
        cursor = db.execute("SELECT id FROM users WHERE username = ?", ('admin',))
        admin_row = cursor.fetchone()
        admin_id = admin_row['id'] if admin_row else None

        cursor = db.execute("SELECT id FROM users WHERE username = ?", ('autonomo',))
        autonomo_row = cursor.fetchone()
        autonomo_id = autonomo_row['id'] if autonomo_row else None

        if not admin_id or not autonomo_id:
            print("[FATAL] Could not find admin or autonomo user to seed tickets. Aborting.", file=sys.stderr, flush=True)
            return

        db.execute("INSERT INTO tickets (cliente_id, direccion_id, tipo, prioridad, estado, asignado_a, creado_por, descripcion, titulo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (1, 1, 'Fontanería', 'Alta', 'Abierto', autonomo_id, admin_id, 'Fuga de agua en el baño principal.', 'Reparar fuga de agua'))
        db.execute("INSERT INTO tickets (cliente_id, direccion_id, tipo, prioridad, estado, asignado_a, creado_por, descripcion, titulo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (2, 2, 'Electricidad', 'Media', 'En Progreso', autonomo_id, admin_id, 'Instalar 5 puntos de luz LED en falso techo.', 'Instalación luces LED'))
        print("[INFO] tickets seeded successfully.", flush=True)

        print("[INFO] Committing changes to the database.", flush=True)
        db.commit()
        print("[INFO] Changes committed successfully.", flush=True)

    except Exception as e:
        print(f"[FATAL] An error occurred during database initialization: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        if 'db' in locals() and db is not None:
            db.rollback()
            print("[INFO] Database changes rolled back.", flush=True)
    finally:
        print("--- [END] Database Initialization ---", flush=True)


def _execute_sql(sql, params=(), cursor=None, fetchone=False, fetchall=False, commit=False):
    """
    A helper function to execute SQL queries.
    """
    if cursor is None:
        db = get_db()
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

def register_commands(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Initializes the database from the master schema file."""
        init_db_func()
        click.echo("Initialized the database with full schema.")

    @app.cli.command("send-reminders")
    def send_reminders_command():
        """Sends WhatsApp reminders for upcoming services."""
        with current_app.app_context():
            db = get_db()
            if db is None:
                click.echo("Error: Could not connect to database.")
                return

            from datetime import datetime, timedelta
            from backend.notifications import send_whatsapp_notification

            # --- Next Day Reminders ---
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            upcoming_services = db.execute(
                '''
                SELECT
                    t.id AS ticket_id,
                    t.descripcion AS ticket_description,
                    e.inicio AS service_start_time,
                    u.id AS technician_user_id,
                    u.username AS technician_username,
                    u.whatsapp_number AS technician_whatsapp,
                    u.whatsapp_opt_in AS technician_opt_in,
                    cl.id AS client_id,
                    cl.nombre AS client_name,
                    cl.telefono AS client_phone,
                    cl.email AS client_email,
                    d.linea1 AS client_address_line1,
                    d.ciudad AS client_address_city,
                    d.provincia AS client_address_province,
                    d.cp AS client_address_cp
                FROM tickets t
                JOIN eventos e ON t.id = e.ticket_id
                LEFT JOIN users u ON e.tecnico_id = u.id
                LEFT JOIN clientes cl ON t.cliente_id = cl.id
                LEFT JOIN direcciones d ON t.direccion_id = d.id
                WHERE SUBSTR(e.inicio, 1, 10) = ? AND e.estado = 'planificado'
                ''',
                (tomorrow,)
            ).fetchall()

            click.echo(f"Checking for services scheduled for {tomorrow}...")
            for service in upcoming_services:
                message = (
                    f"¡Hola {service['technician_username']}! Tienes un servicio programado para mañana, "
                    f"el {service['service_start_time']} para el trabajo: '{service['ticket_description']}'.\n"
                    f"Cliente: {service['client_name']} - Teléfono: {service['client_phone']}\n"
                    f"Dirección: {service['client_address_line1']}, {service['client_address_city']} ({service['client_address_cp']})"
                )

                # Notify technician
                if service['technician_user_id'] and service['technician_opt_in'] and service['technician_whatsapp']:
                    send_whatsapp_notification(db, service['technician_user_id'], message)
                    click.echo(f"Sent reminder to technician {service['technician_username']}.")

                # Notify client
                # For simplicity, let's assume client_id is enough for now, and send_whatsapp_notification will handle it.
                # This means send_whatsapp_notification needs to be updated to accept a client_id or just whatsapp_number.
                # For now, I will just use the client's whatsapp_number directly.
                if service['client_id'] and service['client_opt_in'] and service['client_whatsapp']:
                    client_message = (
                        f"¡Hola {service['client_name']}! Le recordamos que su servicio para el trabajo "
                        f"'{service['ticket_description']}' está programado para mañana, "
                        f"el {service['service_start_time']}.\n"
                        f"El técnico asignado es {service['technician_username']}.\n"
                        f"Dirección: {service['client_address_line1']}, {service['client_address_city']} ({service['client_address_cp']})"
                    )
                    # Assuming send_whatsapp_notification can take client_id and fetch number
                    send_whatsapp_notification(db, service['client_id'], client_message)
                    click.echo(f"Sent reminder to client {service['client_name']}.")

            click.echo("Reminder check completed.")

def log_error(level, message, details=None):
    try:
        db = get_db()
        db.execute(
            "INSERT INTO error_log(level, message, details) VALUES (?,?,?)",
            (level, message, details),
        )
        db.commit()
    except Exception as e:
        # Avoid crashing if logging itself fails
        print(f"Failed to log error to DB: {e}")