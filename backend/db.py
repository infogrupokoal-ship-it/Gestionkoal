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
        with current_app.open_resource("schema.sql") as f:
            schema_sql = f.read().decode("utf-8")
        print(f"init_db_func: Schema.sql leído. Longitud: {len(schema_sql)}", flush=True)
    except Exception as e:
        print(f"ERROR: init_db_func: Fallo al leer schema.sql: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return

    print("init_db_func: Ejecutando script SQL...", flush=True)
    try:
        db.executescript(schema_sql)
        print("init_db_func: Script SQL ejecutado con éxito.", flush=True)

        # Seed roles
        roles = [
            ('admin', 'Administrador'),
            ('oficina', 'Personal de Oficina'),
            ('jefe_obra', 'Jefe de Obra'),
            ('tecnico', 'Técnico'),
            ('autonomo', 'Autónomo'),
            ('cliente', 'Cliente')
        ]
        db.executemany("INSERT INTO roles (code, descripcion) VALUES (?, ?)", roles)
        print("init_db_func: Roles insertados.", flush=True)

        # Seed example users
        admin_password = generate_password_hash('password123')
        users = [
            ('admin', admin_password, 'admin', 'Admin User', 'admin@example.com'),
            ('oficina', admin_password, 'oficina', 'Oficina User', 'oficina@example.com'),
            ('cliente', admin_password, 'cliente', 'Cliente User', 'cliente@example.com'),
            ('autonomo', admin_password, 'autonomo', 'Autonomo User', 'autonomo@example.com')
        ]
        db.executemany("INSERT INTO users (username, password_hash, role, nombre, email) VALUES (?, ?, ?, ?, ?)", users)
        print("init_db_func: Usuarios de ejemplo insertados.", flush=True)

        # Seed user_roles for example users
        user_roles = []
        for user_role in ['admin', 'oficina', 'cliente', 'autonomo']:
            user_id = db.execute(f"SELECT id FROM users WHERE username = '{user_role}'").fetchone()['id']
            role_id = db.execute(f"SELECT id FROM roles WHERE code = '{user_role}'").fetchone()['id']
            user_roles.append((user_id, role_id))
        db.executemany("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", user_roles)
        print("init_db_func: user_roles insertados para usuarios de ejemplo.", flush=True)

        # Seed Clientes
        db.execute("INSERT INTO clientes (nombre, telefono, email, nif) VALUES (?, ?, ?, ?)", ('Cliente Demo 1', '111222333', 'cliente1@example.com', '12345678A'))
        db.execute("INSERT INTO clientes (nombre, telefono, email, nif, is_ngo) VALUES (?, ?, ?, ?, ?)", ('ONG Ayuda Social', '444555666', 'ong@example.com', 'G12345678', 1))
        print("init_db_func: Clientes de ejemplo insertados.", flush=True)

        # Seed Direcciones
        db.execute("INSERT INTO direcciones (cliente_id, linea1, ciudad, provincia, cp) VALUES (?, ?, ?, ?, ?)", (1, 'Calle Falsa 123', 'Valencia', 'Valencia', '46001'))
        db.execute("INSERT INTO direcciones (cliente_id, linea1, ciudad, provincia, cp) VALUES (?, ?, ?, ?, ?)", (2, 'Avenida Siempre Viva 742', 'Madrid', 'Madrid', '28001'))
        print("init_db_func: Direcciones de ejemplo insertadas.", flush=True)

        # Seed Servicios
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
        print("init_db_func: Servicios de ejemplo insertados.", flush=True)

        # Seed Materiales
        materiales = [
            ('MAT001', 'Tornillos Estrella 4x40', 'Ferretería', 'caja 100u', 100, 10, 'Almacén A1', 5.50),
            ('MAT002', 'Cable 2.5mm Negro', 'Electricidad', 'metro', 50, 5, 'Furgoneta 1', 0.75),
            ('PLOM01', 'Cinta de teflón', 'Fontanería', 'rollo', 30, 10, 'Almacén B2', 1.20),
            ('PINT01', 'Rodillo de espuma', 'Pintura', 'unidad', 15, 5, 'Almacén A1', 3.50)
        ]
        db.executemany("INSERT INTO materiales (sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", materiales)
        print("init_db_func: Materiales de ejemplo insertados.", flush=True)

        # Seed Tickets (Jobs)
        admin_id = db.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()['id']
        autonomo_id = db.execute("SELECT id FROM users WHERE username = 'autonomo'").fetchone()['id']
        db.execute("INSERT INTO tickets (cliente_id, direccion_id, tipo, prioridad, estado, asignado_a, creado_por, descripcion, titulo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (1, 1, 'Fontanería', 'Alta', 'Abierto', autonomo_id, admin_id, 'Fuga de agua en el baño principal.', 'Reparar fuga de agua'))
        db.execute("INSERT INTO tickets (cliente_id, direccion_id, tipo, prioridad, estado, asignado_a, creado_por, descripcion, titulo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (2, 2, 'Electricidad', 'Media', 'En Progreso', autonomo_id, admin_id, 'Instalar 5 puntos de luz LED en falso techo.', 'Instalación luces LED'))
        print("init_db_func: Tickets de ejemplo insertados.", flush=True)

        -- provider_quotes: cotizaciones por proveedor y material
        CREATE TABLE IF NOT EXISTS provider_quotes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          provider_id INTEGER NOT NULL,
          material_id INTEGER NOT NULL,
          ticket_id INTEGER,             -- si aplica
          request_msg_id TEXT,           -- id del mensaje enviado
          response_msg_id TEXT,          -- id del msg del proveedor
          requested_qty REAL DEFAULT 1,
          quoted_unit_price REAL,
          currency TEXT DEFAULT 'EUR',
          promised_date TEXT,            -- 'YYYY-MM-DD'
          status TEXT DEFAULT 'pending', -- pending|quoted|rejected|no_stock|confirmed
          raw_text TEXT,                 -- texto literal de la respuesta
          created_at TEXT DEFAULT (datetime('now')),
          updated_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (provider_id) REFERENCES providers(id),
          FOREIGN KEY (material_id) REFERENCES materials(id),
          FOREIGN KEY (ticket_id) REFERENCES tickets(id)
        );

        -- market_research
        CREATE TABLE IF NOT EXISTS market_research (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          material_id INTEGER NOT NULL,
          sector TEXT,
          price_avg REAL,
          price_min REAL,
          price_max REAL,
          sources_json TEXT,            -- JSON con array de {url,price,date,notes}
          difficulty TEXT,              -- facil|medio|dificil
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (material_id) REFERENCES materials(id)
        );

        # Seed Tareas y Gastos para los tickets
        ticket1_id = 1
        ticket2_id = 2
        db.execute("INSERT INTO ticket_tareas (ticket_id, descripcion, estado, asignado_a, creado_por) VALUES (?, ?, ?, ?, ?)", (ticket1_id, 'Comprar junta nueva para el latiguillo.', 'pendiente', autonomo_id, admin_id))
        db.execute("INSERT INTO ticket_tareas (ticket_id, descripcion, estado, asignado_a, creado_por) VALUES (?, ?, ?, ?, ?)", (ticket1_id, 'Cerrar llave de paso general.', 'completado', autonomo_id, admin_id))
        db.execute("INSERT INTO gastos_compartidos (ticket_id, descripcion, monto, pagado_por, creado_por) VALUES (?, ?, ?, ?, ?)", (ticket1_id, 'Compra de junta y teflón', 7.50, autonomo_id, admin_id))
        db.execute("INSERT INTO ticket_tareas (ticket_id, descripcion, estado, asignado_a, creado_por) VALUES (?, ?, ?, ?, ?)", (ticket2_id, 'Pasar guía para el cableado.', 'en_progreso', autonomo_id, admin_id))
        print("init_db_func: Tareas y Gastos de ejemplo insertados.", flush=True)

        db.commit()
    except Exception as e:
        import traceback, sys
        print(f"ERROR: init_db_func: Fallo al ejecutar script SQL o al insertar datos: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        db.rollback()

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