import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin, current_user # Import UserMixin and current_user

from backend.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

class User(UserMixin):
    def __init__(self, id, username, password_hash, role=None):
        self.id = str(id)
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def has_permission(self, perm: str) -> bool:
        # Implement your permission logic here
        # For now, a simple check based on the 'role' column
        # This needs to be expanded with a proper roles/permissions system
        if self.role == 'admin':
            return True # Admin has all permissions
        if perm == 'view_dashboard' and self.role in ['admin', 'oficina', 'jefe_obra', 'tecnico', 'autonomo', 'cliente']:
            return True
        # Add more specific permission checks here
        return False

    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return User(row["id"], row["username"], row["password_hash"], row["role"])

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        db = get_db()
        error = None

        if not username:
            error = 'El nombre de usuario es obligatorio.'
        elif not password:
            error = 'La contraseña es obligatoria.'
        elif not role:
            error = 'El rol es obligatorio.'

        if error is None:
            try:
                # 1. Create User
                cursor = db.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), role),
                )
                user_id = cursor.lastrowid

                # 2. Assign Role
                role_id_row = db.execute("SELECT id FROM roles WHERE code = ?", (role,)).fetchone()
                if role_id_row is None:
                    raise Exception(f"El rol '{role}' no es válido.")
                role_id = role_id_row['id']
                db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))

                # 3. Create Sample Client
                client_cursor = db.execute(
                    "INSERT INTO clientes (nombre, email, telefono) VALUES (?, ?, ?)",
                    (f"Cliente de Ejemplo ({username})", f"cliente.ejemplo@{username}.com", "600111222")
                )
                client_id = client_cursor.lastrowid

                # 4. Create Sample Address for Client
                addr_cursor = db.execute(
                    "INSERT INTO direcciones (cliente_id, linea1, ciudad, cp) VALUES (?, ?, ?, ?)",
                    (client_id, "Calle Falsa 123", "Ejemploville", "00000")
                )
                addr_id = addr_cursor.lastrowid

                # 5. Create Sample Job (Ticket)
                db.execute(
                    "INSERT INTO tickets (cliente_id, direccion_id, asignado_a, creado_por, descripcion, estado, prioridad, tipo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (client_id, addr_id, user_id, user_id, 'Este es un trabajo de demostración creado para ti. ¡Explóralo!', 'Abierto', 'Media', 'Reparación')
                )

                # 6. Create Welcome Notification
                db.execute(
                    "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                    (user_id, '¡Bienvenido! Hemos creado un cliente y un trabajo de ejemplo para ti.')
                )

                # 7. Commit everything
                db.commit()

            except db.IntegrityError:
                error = f"El usuario {username} ya está registrado."
                db.rollback()
            except Exception as e:
                error = f"No se pudo crear el usuario y los datos de ejemplo. Error: {e}"
                db.rollback()
            
            if error is None:
                flash("¡Usuario registrado con éxito! Ahora puedes iniciar sesión.")
                return redirect(url_for("auth.login"))

        flash(error)

    # Fetch roles for registration form dropdown
    db = get_db()
    roles = db.execute('SELECT code, descripcion FROM roles').fetchall()
    return render_template('register.html', roles=roles)

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user_row = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if user_row is None:
            error = 'Nombre de usuario incorrecto.'
        elif not check_password_hash(user_row['password_hash'], password):
            error = 'Contraseña incorrecta.'

        if error is None:
            from flask_login import login_user
            user_obj = User.from_row(user_row)
            login_user(user_obj)
            return redirect(url_for('index')) # Redirect to root index route

        flash(error)

    return render_template('login.html')


@bp.route("/register/client", methods=["GET", "POST"])
def register_client():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        full_name = request.form.get("full_name")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")
        dni = request.form.get("dni")

        db = get_db()
        error = None

        if not username: error = "Se requiere un nombre de usuario."
        elif not password: error = "Se requiere una contraseña."
        elif password != confirm_password: error = "Las contraseñas no coinciden."
        
        if error is None:
            try:
                # Check for existing user/email before trying to insert
                if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
                    raise db.IntegrityError(f"El usuario {username} ya está registrado.")
                if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                    raise db.IntegrityError(f"El email {email} ya está registrado.")

                # 1. Create User
                password_hash = generate_password_hash(password)
                user_cursor = db.execute(
                    "INSERT INTO users (username, email, password_hash, role, nombre, telefono, nif) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (username, email, password_hash, 'cliente', full_name, phone_number, dni),
                )
                user_id = user_cursor.lastrowid

                # 2. Assign 'client' role in user_roles
                role_row = db.execute("SELECT id FROM roles WHERE code = 'cliente'").fetchone()
                if role_row is None:
                    raise Exception("El rol 'cliente' no existe en la base de datos. Ejecuta los seeds de roles.")
                client_role_id = role_row["id"]
                db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, client_role_id))

                # 3. Insert client-specific data
                client_cursor = db.execute(
                    "INSERT INTO clientes (nombre, telefono, email, nif) VALUES (?, ?, ?, ?)",
                    (full_name, phone_number, email, dni)
                )
                cliente_id = client_cursor.lastrowid

                # 4. Insert address
                addr_cursor = db.execute(
                    "INSERT INTO direcciones (cliente_id, linea1) VALUES (?, ?)",
                    (cliente_id, address)
                )
                addr_id = addr_cursor.lastrowid

                # 5. Create Sample Job (Ticket)
                db.execute(
                    "INSERT INTO tickets (cliente_id, direccion_id, asignado_a, creado_por, descripcion, estado, prioridad, tipo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (cliente_id, addr_id, user_id, user_id, 'Este es tu primer trabajo de demostración. ¡Bienvenido!', 'Abierto', 'Media', 'Instalación')
                )

                # 6. Create Welcome Notification
                db.execute(
                    "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                    (user_id, '¡Bienvenido! Hemos creado un trabajo de ejemplo para que puedas empezar.')
                )

                db.commit()
                flash("¡Cliente registrado con éxito! Ahora puedes iniciar sesión.")
                return redirect(url_for("auth.login"))

            except db.IntegrityError as e:
                error = str(e)
                db.rollback()
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
                db.rollback()
        
        flash(error)

    return render_template("register_client.html")

@bp.route("/register/freelancer", methods=["GET", "POST"])
def register_freelancer():
    if request.method == "POST":
        # User fields
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        full_name = request.form.get("full_name")
        phone_number = request.form.get("phone_number")
        dni = request.form.get("dni")

        # Freelancer specific fields
        category = request.form.get("category")
        specialty = request.form.get("specialty")
        city_province = request.form.get("city_province")
        
        db = get_db()
        error = None

        if not username: error = "Se requiere un nombre de usuario."
        elif not password: error = "Se requiere una contraseña."
        elif password != confirm_password: error = "Las contraseñas no coinciden."

        if error is None:
            try:
                if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
                    raise db.IntegrityError(f"El usuario {username} ya está registrado.")
                if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                    raise db.IntegrityError(f"El email {email} ya está registrado.")

                # 1. Create User
                password_hash = generate_password_hash(password)
                user_cursor = db.execute(
                    "INSERT INTO users (username, email, password_hash, role, nombre, telefono, nif) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (username, email, password_hash, 'autonomo', full_name, phone_number, dni),
                )
                user_id = user_cursor.lastrowid

                # 2. Assign 'autonomo' role
                role_row = db.execute("SELECT id FROM roles WHERE code = 'autonomo'").fetchone()
                if role_row is None:
                    raise Exception("El rol 'autonomo' no existe en la base de datos. Ejecuta los seeds de roles.")
                autonomo_role_id = role_row["id"]
                db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, autonomo_role_id))

                # 3. Insert freelancer-specific data
                db.execute(
                    "INSERT INTO freelancers (user_id, category, specialty, city_province) VALUES (?, ?, ?, ?)",
                    (user_id, category, specialty, city_province)
                )

                # 4. Create a generic sample client and address for the ticket
                client_cursor = db.execute(
                    "INSERT INTO clientes (nombre, email, telefono) VALUES (?, ?, ?)",
                    (f"Cliente de Demo para {username}", f"demo.cliente@{username}.com", "600999888")
                )
                cliente_id = client_cursor.lastrowid
                addr_cursor = db.execute(
                    "INSERT INTO direcciones (cliente_id, linea1, ciudad, cp) VALUES (?, ?, ?, ?)",
                    (cliente_id, "Avenida de los Ejemplos 42", "Demoville", "00000")
                )
                addr_id = addr_cursor.lastrowid

                # 5. Create Sample Job (Ticket) assigned to the new freelancer
                db.execute(
                    "INSERT INTO tickets (cliente_id, direccion_id, asignado_a, creado_por, descripcion, estado, prioridad, tipo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (cliente_id, addr_id, user_id, user_id, 'Este es un trabajo de demostración asignado a ti. ¡Bienvenido!', 'Abierto', 'Baja', 'Mantenimiento')
                )

                # 6. Create Welcome Notification
                db.execute(
                    "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                    (user_id, '¡Bienvenido! Te hemos asignado un trabajo de ejemplo para que empieces.')
                )

                db.commit()
                flash("¡Autónomo registrado con éxito! Ahora puedes iniciar sesión.")
                return redirect(url_for("auth.login"))

            except db.IntegrityError as e:
                error = str(e)
                db.rollback()
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
                db.rollback()

        flash(error)

    return render_template("register_freelancer.html")

@bp.route("/register/provider", methods=["GET", "POST"])
def register_provider():
    if request.method == "POST":
        # User fields
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        
        # Provider specific fields
        company_name = request.form.get("company_name")
        contact_person = request.form.get("contact_person")
        provider_phone = request.form.get("provider_phone")
        provider_email = request.form.get("provider_email")

        db = get_db()
        error = None

        if not username: error = "Se requiere un nombre de usuario."
        elif not password: error = "Se requiere una contraseña."
        elif password != confirm_password: error = "Las contraseñas no coinciden."

        if error is None:
            try:
                if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
                    raise db.IntegrityError(f"El usuario {username} ya está registrado.")
                if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                    raise db.IntegrityError(f"El email {email} ya está registrado.")

                # 1. Create User
                password_hash = generate_password_hash(password)
                user_cursor = db.execute(
                    "INSERT INTO users (username, email, password_hash, role, nombre) VALUES (?, ?, ?, ?, ?)",
                    (username, email, password_hash, 'proveedor', company_name or contact_person),
                )
                user_id = user_cursor.lastrowid

                # 2. Assign 'proveedor' role
                proveedor_role_id = db.execute("SELECT id FROM roles WHERE code = 'proveedor'").fetchone()["id"]
                db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, proveedor_role_id))

                # 3. Insert provider-specific data
                db.execute(
                    "INSERT INTO proveedores (nombre, telefono, email) VALUES (?, ?, ?)",
                    (company_name, provider_phone, provider_email)
                )

                # 4. Create Welcome Notification
                db.execute(
                    "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                    (user_id, '¡Bienvenido! Gracias por registrarte como proveedor.')
                )

                db.commit()
                flash("¡Proveedor registrado con éxito! Ahora puedes iniciar sesión.")
                return redirect(url_for("auth.login"))

            except db.IntegrityError as e:
                error = str(e)
                db.rollback()
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
                db.rollback()

        flash(error)

    return render_template("register_provider.html")

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

