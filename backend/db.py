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
from backend.notifications import send_whatsapp_notification

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
    db_path = current_app.config["DATABASE"]
    if os.path.exists(db_path):
        print(f"init_db_func: Deleting existing database at {db_path}", flush=True)
        os.remove(db_path)

    db = get_db()
    if db is None:
        print("ERROR: init_db_func: get_db() returned None.", flush=True)
        return

    print("init_db_func: Intentando abrir schema.sql...", flush=True)
    try:
        # Read the SQLite-compatible schema file from backend/schema.sql
        with current_app.open_resource("schema.sql") as f: # This will look in backend/schema.sql
            schema_sql = f.read().decode("utf-8")
        print(f"init_db_func: Schema.sql leído. Longitud: {len(schema_sql)}", flush=True)
    except Exception as e:
        print(f"ERROR: init_db_func: Fallo al leer schema.sql: {e}", file=sys.stderr, flush=True)
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        return

    print("init_db_func: Ejecutando script SQL...", flush=True)
    try:
        db.executescript(schema_sql)
        print("init_db_func: Script SQL ejecutado con éxito.", flush=True)

        # Seed roles
        db.execute("INSERT INTO roles (code, descripcion) VALUES (?, ?)", ('admin', 'Administrador'))
        db.execute("INSERT INTO roles (code, descripcion) VALUES (?, ?)", ('oficina', 'Personal de Oficina'))
        db.execute("INSERT INTO roles (code, descripcion) VALUES (?, ?)", ('jefe_obra', 'Jefe de Obra'))
        db.execute("INSERT INTO roles (code, descripcion) VALUES (?, ?)", ('tecnico', 'Técnico'))
        db.execute("INSERT INTO roles (code, descripcion) VALUES (?, ?)", ('autonomo', 'Autónomo'))
        db.execute("INSERT INTO roles (code, descripcion) VALUES (?, ?)", ('cliente', 'Cliente'))
        print("init_db_func: Roles insertados.", flush=True)

        # Seed example users
        admin_password = generate_password_hash('password123')
        db.execute(
            "INSERT INTO users (username, password_hash, role, nombre, email) VALUES (?, ?, ?, ?, ?)",
            ('admin', admin_password, 'admin', 'Admin User', 'admin@example.com')
        )
        db.execute(
            "INSERT INTO users (username, password_hash, role, nombre, email) VALUES (?, ?, ?, ?, ?)",
            ('oficina', admin_password, 'oficina', 'Oficina User', 'oficina@example.com')
        )
        db.execute(
            "INSERT INTO users (username, password_hash, role, nombre, email) VALUES (?, ?, ?, ?, ?)",
            ('cliente', admin_password, 'cliente', 'Cliente User', 'cliente@example.com')
        )
        db.execute(
            "INSERT INTO users (username, password_hash, role, nombre, email) VALUES (?, ?, ?, ?, ?)",
            ('autonomo', admin_password, 'autonomo', 'Autonomo User', 'autonomo@example.com')
        )
        print("init_db_func: Usuarios de ejemplo insertados.", flush=True)

        # Seed user_roles for example users
        admin_id = db.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()['id']
        oficina_id = db.execute("SELECT id FROM users WHERE username = 'oficina'").fetchone()['id']
        cliente_id = db.execute("SELECT id FROM users WHERE username = 'cliente'").fetchone()['id']
        autonomo_id = db.execute("SELECT id FROM users WHERE username = 'autonomo'").fetchone()['id']

        admin_role_id = db.execute("SELECT id FROM roles WHERE code = 'admin'").fetchone()['id']
        oficina_role_id = db.execute("SELECT id FROM roles WHERE code = 'oficina'").fetchone()['id']
        cliente_role_id = db.execute("SELECT id FROM roles WHERE code = 'cliente'").fetchone()['id']
        autonomo_role_id = db.execute("SELECT id FROM roles WHERE code = 'autonomo'").fetchone()['id']

        db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (admin_id, admin_role_id))
        db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (oficina_id, oficina_role_id))
        db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (cliente_id, cliente_role_id))
        db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (autonomo_id, autonomo_role_id))
        print("init_db_func: user_roles insertados para usuarios de ejemplo.", flush=True)

        # Seed Clientes
        db.execute("INSERT INTO clientes (nombre, telefono, email, nif) VALUES (?, ?, ?, ?)", ('Cliente Demo 1', '111222333', 'cliente1@example.com', '12345678A'))
        db.execute("INSERT INTO clientes (nombre, telefono, email, nif) VALUES (?, ?, ?, ?)", ('Cliente Demo 2', '444555666', 'cliente2@example.com', '87654321B'))
        print("init_db_func: Clientes de ejemplo insertados.", flush=True)

        # Seed Direcciones (assuming client_id 1 and 2 exist)
        db.execute("INSERT INTO direcciones (cliente_id, linea1, ciudad, provincia, cp) VALUES (?, ?, ?, ?, ?)", (1, 'Calle Falsa 123', 'Valencia', 'Valencia', '46001'))
        db.execute("INSERT INTO direcciones (cliente_id, linea1, ciudad, provincia, cp) VALUES (?, ?, ?, ?, ?)", (2, 'Avenida Siempre Viva 742', 'Madrid', 'Madrid', '28001'))
        print("init_db_func: Direcciones de ejemplo insertadas.", flush=True)

        # Seed Equipos (assuming direccion_id 1 and 2 exist)
        db.execute("INSERT INTO equipos (direccion_id, marca, modelo) VALUES (?, ?, ?)", (1, 'Marca A', 'Modelo X'))
        db.execute("INSERT INTO equipos (direccion_id, marca, modelo) VALUES (?, ?, ?)", (2, 'Marca B', 'Modelo Y'))
        print("init_db_func: Equipos de ejemplo insertados.", flush=True)

        # Seed Servicios
        db.execute("INSERT INTO services (name, description, price) VALUES (?, ?, ?)", ('Reparación General', 'Reparación de averías comunes', 50.00))
        db.execute("INSERT INTO services (name, description, price) VALUES (?, ?, ?)", ('Mantenimiento Preventivo', 'Revisión anual y limpieza', 75.00))
        print("init_db_func: Servicios de ejemplo insertados.", flush=True)

        # Seed Materiales
        db.execute("INSERT INTO materiales (sku, nombre, categoria, unidad, stock, stock_min, ubicacion) VALUES (?, ?, ?, ?, ?, ?, ?)", ('MAT001', 'Tornillos', 'Ferreteria', 'unidad', 100, 10, 'Almacen'))
        db.execute("INSERT INTO materiales (sku, nombre, categoria, unidad, stock, stock_min, ubicacion) VALUES (?, ?, ?, ?, ?, ?, ?)", ('MAT002', 'Cable 2.5mm', 'Electricidad', 'metro', 50, 5, 'Furgoneta 1'))
        print("init_db_func: Materiales de ejemplo insertados.", flush=True)

        # Seed Proveedores
        db.execute("INSERT INTO proveedores (nombre, telefono, email) VALUES (?, ?, ?)", ('Proveedor A', '987654321', 'proveedorA@example.com'))
        db.execute("INSERT INTO proveedores (nombre, telefono, email, tipo_proveedor, contacto_persona, direccion, cif, web, notas, condiciones_pago) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('Proveedor B', '123123123', 'proveedorB@example.com', 'Servicio', 'Maria Lopez', 'Avenida Siempre Viva 2, Madrid', 'B87654321', 'https://www.proveedorb.com', 'Notas sobre Proveedor B', '60 días'))
        print("init_db_func: Proveedores de ejemplo insertados.", flush=True)

        # Seed Herramientas
        db.execute("INSERT INTO herramientas (codigo, nombre, estado) VALUES (?, ?, ?)", ('HER001', 'Taladro Percutor', 'Operativo'))
        db.execute("INSERT INTO herramientas (codigo, nombre, estado) VALUES (?, ?, ?)", ('HER002', 'Multímetro Digital', 'En Mantenimiento'))
        print("init_db_func: Herramientas de ejemplo insertadas.", flush=True)

        # Seed Tickets (Jobs) - assuming client_id 1, direccion_id 1, equipo_id 1, and user_id for admin/autonomo exist
        db.execute(
            "INSERT INTO tickets (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, creado_por, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (1, 1, 1, 'Llamada', 'Reparación', 'Alta', 'Abierto', '2025-09-20', autonomo_id, admin_id, 'Fallo en sistema de climatización.')
        )
        db.execute(
            "INSERT INTO tickets (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, creado_por, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (2, 2, 2, 'Web', 'Mantenimiento', 'Media', 'En Progreso', '2025-09-25', autonomo_id, oficina_id, 'Mantenimiento preventivo anual.')
        )
        print("init_db_func: Tickets de ejemplo insertados.", flush=True)

        db.commit() # Commit after all inserts
    except Exception as e:
        import traceback, sys
        print(f"ERROR: init_db_func: Fallo al ejecutar script SQL o al insertar datos: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        db.rollback() # Rollback any partial changes

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
                    cl.whatsapp_number AS client_whatsapp,
                    cl.whatsapp_opt_in AS client_opt_in
                FROM tickets t
                JOIN eventos e ON t.id = e.ticket_id
                LEFT JOIN users u ON e.tecnico_id = u.id
                LEFT JOIN clientes cl ON t.cliente_id = cl.id
                WHERE SUBSTR(e.inicio, 1, 10) = ? AND e.estado = 'planificado'
                ''',
                (tomorrow,)
            ).fetchall()

            click.echo(f"Checking for services scheduled for {tomorrow}...")
            for service in upcoming_services:
                message = f"Recordatorio: Tienes un servicio programado para mañana, {service['service_start_time']}, para el trabajo: {service['ticket_description']}."

                # Notify technician
                if service['technician_user_id'] and service['technician_opt_in'] and service['technician_whatsapp']:
                    send_whatsapp_notification(db, service['technician_user_id'], message)
                    click.echo(f"Sent reminder to technician {service['technician_username']}.")

                # Notify client
                # For simplicity, let's assume client_id is enough for now, and send_whatsapp_notification will handle it.
                # This means send_whatsapp_notification needs to be updated to accept a client_id or just whatsapp_number.
                # For now, I will just use the client's whatsapp_number directly.
                if service['client_id'] and service['client_opt_in'] and service['client_whatsapp']:
                    client_message = f"Recordatorio: Su servicio para el trabajo '{service['ticket_description']}' está programado para mañana, {service['service_start_time']}."
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