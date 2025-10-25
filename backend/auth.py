import functools
import secrets
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import UserMixin, current_user  # Import UserMixin and current_user
from werkzeug.security import check_password_hash, generate_password_hash

from backend.db_utils import get_db
from backend.wa_client import send_whatsapp_text  # Import send_whatsapp_text

bp = Blueprint('auth', __name__, url_prefix='/auth')

def _create_user_and_role(db, username, password, role, email, full_name, phone_number, nif, whatsapp_number):
    """Helper function to create a user and assign a role."""
    # 1. Check for existing user/email before trying to insert
    if db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
        raise db.IntegrityError(f"El usuario {username} ya está registrado.")
    if email and db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        raise db.IntegrityError(f"El email {email} ya está registrado.")

    # 2. Generate WhatsApp confirmation code
    whatsapp_code = secrets.token_hex(3).upper()
    whatsapp_code_expires = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

    # 3. Create User
    password_hash = generate_password_hash(password)
    user_cursor = db.execute(
        "INSERT INTO users (username, email, password_hash, role, nombre, telefono, nif, whatsapp_number, whatsapp_code, whatsapp_code_expires, whatsapp_verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (username, email, password_hash, role, full_name, phone_number, nif, whatsapp_number, whatsapp_code, whatsapp_code_expires, 0),
    )
    user_id = user_cursor.lastrowid

    # 4. Assign Role
    role_row = db.execute("SELECT id FROM roles WHERE code = ?", (role,)).fetchone()
    if role_row is None:
        raise Exception(f"El rol '{role}' no es válido.")
    role_id = role_row["id"]
    db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))

    # 5. Send WhatsApp confirmation code
    message = f"Tu código de confirmación para GestionKoal es: {whatsapp_code}. Válido por 10 minutos."
    send_whatsapp_text(whatsapp_number, message)

    return user_id

class User(UserMixin):


    def __init__(self, id, username, password_hash, role=None, whatsapp_verified=0):
        self.id = str(id)
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.whatsapp_verified = whatsapp_verified

    def has_permission(self, permission_code):
        from flask import g
        if getattr(g, "SKIP_PERMISSION_CHECKS", False):
            return True
        # This is a more efficient, hardcoded RBAC check.
        # It avoids hitting the database for every permission check.
        permissions_map = {
            'admin': {'view_dashboard', 'manage_all_jobs', 'manage_clients', 'view_reports', 'manage_users', 'approve_quotes', 'manage_quotes', 'create_quotes'},
            'oficina': {
                'view_dashboard', 'manage_all_jobs', 'manage_clients', 'view_reports', 'manage_quotes', 'create_quotes'
            },
            'jefe_obra': {
                'view_dashboard', 'manage_all_jobs'
            },
            'tecnico': {
                'view_dashboard', 'manage_own_jobs'
            },
            'autonomo': {
                'view_dashboard', 'manage_own_jobs', 'create_quotes'
            },
            'cliente': {
                'view_dashboard', 'view_own_jobs'
            }
        }
        # Get the set of permissions for the user's role, default to empty set if role is None or not in map
        user_permissions = permissions_map.get(self.role, set())
        # Check if the required permission is in the user's set of permissions
        return permission_code in user_permissions


    @staticmethod
    def from_row(row):
        if row is None:
            return None
        return User(row["id"], row["username"], row["password_hash"], row["role"], row["whatsapp_verified"])

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        whatsapp_number = request.form.get('whatsapp_number')
        error = None

        db = get_db()
        if db is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('auth.register'))

        if not username:
            error = 'El nombre de usuario es obligatorio.'
        elif not password:
            error = 'La contraseña es obligatoria.'
        elif not role:
            error = 'El rol es obligatorio.'
        elif not whatsapp_number:
            error = 'El número de WhatsApp es obligatorio para la verificación.'

        if error is None:
            try:
                user_id = _create_user_and_role(
                    db=db,
                    username=username,
                    password=password,
                    role=role,
                    email=email,
                    full_name=username, # Use username as full_name for generic registration
                    phone_number=None,
                    nif=None,
                    whatsapp_number=whatsapp_number
                )

                db.commit()
                flash("¡Registro exitoso! Se ha enviado un código de confirmación a tu número de WhatsApp.")
                return redirect(url_for("auth.whatsapp_confirm", user_id=user_id))

            except (db.IntegrityError, Exception) as e:
                error = str(e)
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
        error = None

        db = get_db()
        if db is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('auth.login'))
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


@bp.route('/register_client', methods=('GET', 'POST'))
def register_client():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form['full_name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        dni = request.form['dni']
        whatsapp_number = request.form.get('whatsapp_number')
        is_ngo = 'is_ngo' in request.form

        db = get_db()
        if db is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('auth.register_client'))

        if not username:
            error = "Se requiere un nombre de usuario."
        elif not password:
            error = "Se requiere una contraseña."
        elif password != confirm_password:
            error = "Las contraseñas no coinciden."
        elif not whatsapp_number:
            error = "El número de WhatsApp es obligatorio para la verificación."

        if error is None:
            try:
                user_id = _create_user_and_role(
                    db=db,
                    username=username,
                    password=password,
                    role='cliente',
                    email=email,
                    full_name=full_name,
                    phone_number=phone_number,
                    nif=dni,
                    whatsapp_number=whatsapp_number
                )

                # 3. Insert client-specific data
                client_cursor = db.execute(
                    "INSERT INTO clientes (nombre, telefono, email, nif, is_ngo) VALUES (?, ?, ?, ?, ?)",
                    (full_name, phone_number, email, dni, is_ngo)
                )
                cliente_id = client_cursor.lastrowid

                # 4. Insert address (assuming address is also from form)
                address = request.form.get('address')
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
                flash("¡Registro exitoso! Se ha enviado un código de confirmación a tu número de WhatsApp.")
                return redirect(url_for("auth.whatsapp_confirm", user_id=user_id))

            except (db.IntegrityError, Exception) as e:
                print(f"ERROR EN REGISTRO DE CLIENTE: {e}") # <-- Temporary line for debugging
                error = str(e)
                db.rollback()

        flash(error)

    return render_template("register_client.html")

@bp.route('/register_freelancer', methods=('GET', 'POST'))
def register_freelancer():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form['full_name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        dni = request.form['dni']
        whatsapp_number = request.form.get('whatsapp_number')
        category = request.form.get('category')
        specialty = request.form.get('specialty')
        city_province = request.form.get('city_province')
        web = request.form.get('web')
        notes = request.form.get('notes')
        source_url = request.form.get('source_url')
        hourly_rate_normal = request.form.get('hourly_rate_normal', type=float)
        hourly_rate_tier2 = request.form.get('hourly_rate_tier2', type=float)
        hourly_rate_tier3 = request.form.get('hourly_rate_tier3', type=float)
        difficulty_surcharge_rate = request.form.get('difficulty_surcharge_rate', type=float)
        error = None

        db = get_db()
        if db is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('auth.register_freelancer'))

        if not username:
            error = "Se requiere un nombre de usuario."
        elif not password:
            error = "Se requiere una contraseña."
        elif password != confirm_password:
            error = "Las contraseñas no coinciden."
        elif not whatsapp_number:
            error = "El número de WhatsApp es obligatorio para la verificación."

        if error is None:
            try:
                user_id = _create_user_and_role(
                    db=db,
                    username=username,
                    password=password,
                    role='autonomo',
                    email=email,
                    full_name=full_name,
                    phone_number=phone_number,
                    nif=dni,
                    whatsapp_number=whatsapp_number
                )

                # 3. Insert freelancer-specific data
                db.execute(
                    "INSERT INTO freelancers (user_id, category, specialty, city_province, web, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate, recargo_zona, recargo_dificultad) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, category, specialty, city_province, web, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate, 0.0, 0.0)
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
                flash("¡Registro exitoso! Se ha enviado un código de confirmación a tu número de WhatsApp.")
                return redirect(url_for("auth.whatsapp_confirm", user_id=user_id))

            except (db.IntegrityError, Exception) as e:
                error = str(e)
                db.rollback()

        flash(error)

    return render_template("register_freelancer.html")

@bp.route('/register_provider', methods=('GET', 'POST'))
def register_provider():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        company_name = request.form.get('company_name')
        contact_person = request.form.get('contact_person')
        email = request.form['email']
        provider_phone = request.form.get('provider_phone')

        error = None

        db = get_db()
        if db is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('auth.register_provider'))

        if not username:
            error = "Se requiere un nombre de usuario."
        elif not password:
            error = "Se requiere una contraseña."
        elif password != confirm_password:
            error = "Las contraseñas no coinciden."

        if error is None:
            try:
                user_id = _create_user_and_role(
                    db=db,
                    username=username,
                    password=password,
                    role='proveedor',
                    email=email,
                    full_name=company_name or contact_person,
                    phone_number=provider_phone,
                    nif=None, # NIF is not inserted into users table for providers
                    whatsapp_number=None # No whatsapp verification for providers
                )

                # 3. Insert provider-specific data
                db.execute(
                    "INSERT INTO proveedores (nombre, telefono, email, tipo_proveedor) VALUES (?, ?, ?, ?)",
                    (company_name, provider_phone, email, request.form.get('tipo_proveedor'))
                )

                # 4. Create Welcome Notification
                db.execute(
                    "INSERT INTO notifications (user_id, message) VALUES (?, ?)",
                    (user_id, '¡Bienvenido! Gracias por registrarte como proveedor.')
                )

                db.commit()
                flash("¡Proveedor registrado con éxito! Ahora puedes iniciar sesión.")
                return redirect(url_for("auth.login"))

            except (db.IntegrityError, Exception) as e:
                error = str(e)
                db.rollback()

        flash(error)

    return render_template("register_provider.html")

@bp.route('/whatsapp_confirm/<int:user_id>', methods=('GET', 'POST'))
def whatsapp_confirm(user_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('auth.register'))
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if user is None:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('auth.register'))

    if user['whatsapp_verified']:
        flash('Tu número de WhatsApp ya ha sido verificado.', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form['code'].upper()
        error = None

        if not code:
            error = 'Por favor, introduce el código de confirmación.'
        elif code != user['whatsapp_code']:
            error = 'Código de confirmación incorrecto.'
        elif datetime.now() > datetime.strptime(user['whatsapp_code_expires'], '%Y-%m-%d %H:%M:%S'):
            error = 'El código de confirmación ha caducado. Por favor, solicita uno nuevo.'

        if error is None:
            db.execute(
                'UPDATE users SET whatsapp_verified = 1, whatsapp_code = NULL, whatsapp_code_expires = NULL WHERE id = ?',
                (user_id,)
            )
            db.commit()
            flash('¡Número de WhatsApp verificado con éxito! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/whatsapp_confirm.html', user_id=user_id)

@bp.route('/resend_whatsapp_code/<int:user_id>', methods=('GET',))
def resend_whatsapp_code(user_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('auth.register'))
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if user is None:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('auth.register'))

    if user['whatsapp_verified']:
        flash('Tu número de WhatsApp ya ha sido verificado.', 'info')
        return redirect(url_for('auth.login'))

    try:
        # Generate new WhatsApp confirmation code
        whatsapp_code = secrets.token_hex(3).upper()
        whatsapp_code_expires = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

        db.execute(
            'UPDATE users SET whatsapp_code = ?, whatsapp_code_expires = ? WHERE id = ?',
            (whatsapp_code, whatsapp_code_expires, user_id)
        )
        db.commit()

        # Send new WhatsApp confirmation code
        message = f"Tu nuevo código de confirmación para GestionKoal es: {whatsapp_code}. Válido por 10 minutos."
        send_whatsapp_text(user['whatsapp_number'], message)

        flash('Se ha enviado un nuevo código de confirmación a tu número de WhatsApp.', 'success')
    except Exception as e:
        flash(f'Error al reenviar el código de WhatsApp: {e}', 'error')
        db.rollback()

    return redirect(url_for('auth.whatsapp_confirm', user_id=user_id))

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

INTERNAL_ROLES_NO_WA = {"admin", "oficina", "gestion", "comercial"}

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # Si el rol es interno, NO obligamos a verificar WhatsApp
        try:
            # Asumimos que el rol está en una columna `role` en el objeto user
            user_role = getattr(current_user, "role", None)
            is_internal = user_role in INTERNAL_ROLES_NO_WA
        except Exception:
            is_internal = False

        if (not is_internal) and (not getattr(current_user, "whatsapp_verified", False)):
            # Permitimos entrar a la propia pantalla de confirmación
            if request.endpoint not in ['auth.whatsapp_confirm', 'auth.resend_whatsapp_code']:
                flash('Por favor, verifica tu número de WhatsApp para continuar.', 'warning')
                return redirect(url_for('auth.whatsapp_confirm', user_id=current_user.id))

        return view(**kwargs)

    return wrapped_view
