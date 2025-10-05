# backend/auth.py (fragmento relevante)
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user
from werkzeug.security import check_password_hash
from backend.extensions import db
from backend.models import User   # el de arriba
from . import db as legacy_db # Importar el conector legacy
import secrets
from datetime import datetime, timedelta
from backend.wa_client import send_whatsapp_text
import functools

bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ident = request.form.get("username") or request.form.get("email")
        password = request.form.get("password", "")

        user_row = None
        conn = get_db()
        if conn is None:
            flash("Database connection error.", "error")
            return render_template("login.html"), 200

        row = conn.execute(
            """
            SELECT id, username, email, password_hash,
                   IFNULL(is_active, 1) AS active
            FROM users
            WHERE username = ? OR email = ?
            LIMIT 1
            """,
            (ident, ident),
        ).fetchone()

        if row is not None:
            user_row = dict(row)

        from werkzeug.security import check_password_hash
        if (
            user_row
            and user_row.get("password_hash")
            and check_password_hash(user_row["password_hash"], password)
            and bool(user_row.get("active", 1))
        ):
            from flask_login import login_user
            from backend.models import User

            user = User(
                id=user_row["id"],
                username=user_row["username"],
                email=user_row.get("email"),
                active=user_row.get("active", 1),
            )
            login_user(user, remember=False, fresh=True)
            return redirect(request.args.get("next") or url_for("index"))

        flash("Credenciales incorrectas o usuario inactivo.", "error")
        return render_template("login.html"), 200

    return render_template("login.html")

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        whatsapp_number = request.form.get('whatsapp_number')
        error = None

        db_conn = get_db()
        if db_conn is None:
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
                whatsapp_code = secrets.token_hex(3).upper()
                whatsapp_code_expires = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
                referral_code = secrets.token_hex(5).upper() # Generate a unique referral code

                cursor = db_conn.execute(
                    "INSERT INTO users (username, password_hash, role, email, whatsapp_number, whatsapp_code, whatsapp_code_expires, whatsapp_verified, referral_code, referred_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (username, generate_password_hash(password), role, email, whatsapp_number, whatsapp_code, whatsapp_code_expires, 0, referral_code, None),
                )
                user_id = cursor.lastrowid

                role_id_row = db_conn.execute("SELECT id FROM roles WHERE code = ?", (role,)).fetchone()
                if role_id_row is None:
                    raise Exception(f"El rol '{role}' no es válido.")
                role_id = role_id_row['id']
                db_conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, role_id))

                message = f"Tu código de confirmación para GestionKoal es: {whatsapp_code}. Válido por 10 minutos."
                send_whatsapp_text(whatsapp_number, message)

                db_conn.commit()
                flash("¡Registro exitoso! Se ha enviado un código de confirmación a tu número de WhatsApp.")
                return redirect(url_for("auth.whatsapp_confirm", user_id=user_id))

            except db_conn.IntegrityError:
                error = f"El usuario {username} ya está registrado."
                db_conn.rollback()
            except Exception as e:
                error = f"No se pudo crear el usuario y los datos de ejemplo. Error: {e}"
                db_conn.rollback()

            if error is None:
                flash("¡Usuario registrado con éxito! Ahora puedes iniciar sesión.")
                return redirect(url_for("auth.login"))

        flash(error)

    db_conn = get_db()
    roles = db_conn.execute('SELECT code, descripcion FROM roles').fetchall()
    return render_template('register.html', roles=roles)

@bp.route('/whatsapp_confirm/<int:user_id>', methods=('GET', 'POST'))
def whatsapp_confirm(user_id):
    conn = get_db()
    if conn is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('auth.register'))
    user_row = conn.execute('SELECT *, whatsapp_verified FROM users WHERE id = ?', (user_id,)).fetchone()

    if user_row is None:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('auth.register'))

    user = User(**dict(user_row)) # Convert row to User object

    if user.whatsapp_verified:
        flash('Tu número de WhatsApp ya ha sido verificado.', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form['code'].upper()
        error = None

        if not code:
            error = 'Por favor, introduce el código de confirmación.'
        elif code != user_row['whatsapp_code']:
            error = 'Código de confirmación incorrecto.'
        elif datetime.now() > datetime.strptime(user_row['whatsapp_code_expires'], '%Y-%m-%d %H:%M:%S'):
            error = 'El código de confirmación ha caducado. Por favor, solicita uno nuevo.'

        if error is None:
            conn.execute(
                'UPDATE users SET whatsapp_verified = 1, whatsapp_code = NULL, whatsapp_code_expires = NULL WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            flash('¡Número de WhatsApp verificado con éxito! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/whatsapp_confirm.html', user_id=user_id)

@bp.route('/resend_whatsapp_code/<int:user_id>', methods=('GET',))
def resend_whatsapp_code(user_id):
    conn = get_db()
    if conn is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('auth.register'))
    user_row = conn.execute('SELECT *, whatsapp_verified FROM users WHERE id = ?', (user_id,)).fetchone()

    if user_row is None:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('auth.register'))

    user = User(**dict(user_row)) # Convert row to User object

    if user.whatsapp_verified:
        flash('Tu número de WhatsApp ya ha sido verificado.', 'info')
        return redirect(url_for('auth.login'))

    try:
        whatsapp_code = secrets.token_hex(3).upper()
        whatsapp_code_expires = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

        conn.execute(
            'UPDATE users SET whatsapp_code = ?, whatsapp_code_expires = ? WHERE id = ?',
            (whatsapp_code, whatsapp_code_expires, user_id)
        )
        conn.commit()

        message = f"Tu nuevo código de confirmación para GestionKoal es: {whatsapp_code}. Válido por 10 minutos."
        send_whatsapp_text(user.whatsapp_number, message)

        flash('Se ha enviado un nuevo código de confirmación a tu número de WhatsApp.', 'success')
    except Exception as e:
        flash(f'Error al reenviar el código de WhatsApp: {e}', 'error')
        conn.rollback()

    return redirect(url_for('auth.whatsapp_confirm', user_id=user_id))


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        # if current_user.is_authenticated and not getattr(current_user, 'whatsapp_verified', False):
        #     if request.endpoint != 'auth.whatsapp_confirm':
        #         flash('Por favor, verifica tu número de WhatsApp para continuar.', 'warning')
        #         return redirect(url_for('auth.whatsapp_confirm', user_id=current_user.id))

        return view(**kwargs)

    return wrapped_view