import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from backend.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'] # Assuming role is selected during registration
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
                cursor = db.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), role),
                )
                user_id = cursor.lastrowid
                # Insert into user_roles table
                role_id = db.execute("SELECT id FROM roles WHERE code = ?", (role,)).fetchone()['id']
                db.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))
                db.commit()
            except db.IntegrityError:
                error = f"El usuario {username} ya está registrado."
            else:
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
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Nombre de usuario incorrecto.'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Contraseña incorrecta.'

        if error is None:
            from flask_login import login_user
            login_user(User.from_row(user))
            return redirect(url_for('index')) # Redirect to root index route

        flash(error)

    return render_template('login.html')

@bp.route("/register")
def register_general():
    return render_template("register.html")

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

        conn = get_db()
        error = None

        if not username: error = "Se requiere un nombre de usuario."
        elif not password: error = "Se requiere una contraseña."
        elif password != confirm_password: error = "Las contraseñas no coinciden."
        elif conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone(): error = f"El usuario {username} ya está registrado."
        elif conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone(): error = f"El email {email} ya está registrado."

        if error is None:
            password_hash = generate_password_hash(password)
            cursor = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            user_id = cursor.lastrowid

            # Assign 'client' role
            client_role_id = conn.execute("SELECT id FROM roles WHERE code = 'cliente'").fetchone()["id"]
            conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, client_role_id))

            # Insert client-specific data
            conn.execute(
                "INSERT INTO clientes (user_id, nombre, telefono, email, direccion, dni) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, full_name, phone_number, email, address, dni)
            )
            conn.commit()
            return redirect(url_for("auth.login"))
        
        flash(error) # Use flash for errors

    return render_template("register_client.html")

@bp.route("/register/freelancer", methods=["GET", "POST"])
def register_freelancer():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        full_name = request.form.get("full_name")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")
        dni = request.form.get("dni")

        # Freelancer specific details
        category = request.form.get("category")
        specialty = request.form.get("specialty")
        city_province = request.form.get("city_province")
        web = request.form.get("web")
        notes = request.form.get("notes")
        source_url = request.form.get("source_url")
        hourly_rate_normal = request.form.get("hourly_rate_normal")
        hourly_rate_tier2 = request.form.get("hourly_rate_tier2")
        hourly_rate_tier3 = request.form.get("hourly_rate_tier3")
        difficulty_surcharge_rate = request.form.get("difficulty_surcharge_rate")

        conn = get_db()
        error = None

        if not username: error = "Se requiere un nombre de usuario."
        elif not password: error = "Se requiere una contraseña."
        elif password != confirm_password: error = "Las contraseñas no coinciden."
        elif conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone(): error = f"El usuario {username} ya está registrado."
        elif conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone(): error = f"El email {email} ya está registrado."

        if error is None:
            password_hash = generate_password_hash(password)
            cursor = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            user_id = cursor.lastrowid

            # Assign 'autonomo' role
            autonomo_role_id = conn.execute("SELECT id FROM roles WHERE code = 'autonomo'").fetchone()["id"]
            conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, autonomo_role_id))

            # Insert freelancer-specific data (assuming 'freelancers' table exists)
            # This part needs to be adapted based on the actual 'freelancers' table schema
            # For now, I'll just insert into users and user_roles
            # conn.execute(
            #     "INSERT INTO freelancers (...) VALUES (...)",
            #     (...)
            # )
            conn.commit()
            return redirect(url_for("auth.login"))
        
        flash(error) # Use flash for errors

    return render_template("register_freelancer.html")

@bp.route("/register/provider", methods=["GET", "POST"])
def register_provider():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        full_name = request.form.get("full_name")
        phone_number = request.form.get("phone_number")
        address = request.form.get("address")
        dni = request.form.get("dni")

        # Provider specific details
        company_name = request.form.get("company_name")
        contact_person = request.form.get("contact_person")
        provider_phone = request.form.get("provider_phone")
        provider_email = request.form.get("provider_email")
        provider_address = request.form.get("provider_address")
        service_type = request.form.get("service_type")
        web = request.form.get("web")
        notes = request.form.get("notes")

        conn = get_db()
        error = None

        if not username: error = "Se requiere un nombre de usuario."
        elif not password: error = "Se requiere una contraseña."
        elif password != confirm_password: error = "Las contraseñas no coinciden."
        elif conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone(): error = f"El usuario {username} ya está registrado."
        elif conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone(): error = f"El email {email} ya está registrado."

        if error is None:
            password_hash = generate_password_hash(password)
            cursor = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash),
            )
            user_id = cursor.lastrowid

            # Assign 'proveedor' role
            proveedor_role_id = conn.execute("SELECT id FROM roles WHERE code = 'proveedor'").fetchone()["id"]
            conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, proveedor_role_id))

            # Insert provider-specific data (assuming 'proveedores' table exists)
            # This part needs to be adapted based on the actual 'proveedores' table schema
            # For now, I'll just insert into users and user_roles
            # conn.execute(
            #     "INSERT INTO proveedores (...) VALUES (...)",
            #     (...)
            # )
            conn.commit()
            return redirect(url_for("auth.login"))
        
        flash(error) # Use flash for errors

    return render_template("register_provider.html")

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
