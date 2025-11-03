import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from backend.auth import login_required
from backend.db_utils import get_db

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.route("/")
@login_required
def list_users():
    db = get_db()
    if db is None:
        flash("Database connection error.", "error")
        return redirect(
            url_for("index")
        )  # Redirect to a safe page, e.g., index or login

    users = db.execute(
        """
        SELECT
            u.id, u.username, u.email, u.nombre, u.telefono, u.nif, u.whatsapp_number, u.whatsapp_opt_in,
            GROUP_CONCAT(r.code) AS roles_codes
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        GROUP BY u.id, u.username, u.email, u.nombre, u.telefono, u.nif, u.whatsapp_number, u.whatsapp_opt_in
        ORDER BY u.username
        """
    ).fetchall()
    return render_template("users/list.html", users=users)


@bp.route("/<int:user_id>")
@login_required
def view_user(user_id):
    db = get_db()
    if db is None:
        flash("Database connection error.", "error")
        return redirect(
            url_for("index")
        )  # Redirect to a safe page, e.g., index or login

    user = db.execute(
        """
        SELECT
            u.id, u.username, u.email, u.nombre, u.telefono, u.nif, u.whatsapp_number, u.whatsapp_opt_in,
            u.costo_por_hora, u.tasa_recargo, -- New fields
            GROUP_CONCAT(r.code) AS roles_codes
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        WHERE u.id = ?
        GROUP BY u.id, u.username, u.email, u.nombre, u.telefono, u.nif, u.whatsapp_number, u.whatsapp_opt_in, u.costo_por_hora, u.tasa_recargo
        """,
        (user_id,),
    ).fetchone()

    if user is None:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for("users.list_users"))

    return render_template("users/view.html", user=user)


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_user():
    db = get_db()
    if db is None:
        flash("Database connection error.", "error")
        return redirect(url_for("users.list_users"))
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        nombre = request.form["nombre"]
        apellidos = request.form["apellidos"]
        telefono = request.form["telefono"]
        direccion = request.form["direccion"]
        ciudad = request.form["ciudad"]
        provincia = request.form["provincia"]
        cp = request.form["cp"]
        nif = request.form["nif"]
        selected_role_code = request.form.get("role")
        whatsapp_number = request.form.get("whatsapp_number")
        whatsapp_opt_in = "whatsapp_opt_in" in request.form  # Checkbox value
        costo_por_hora = request.form.get(
            "costo_por_hora", type=float, default=0.0
        )  # New
        tasa_recargo = request.form.get("tasa_recargo", type=float, default=0.0)  # New
        error = None
        if not username:
            error = "El nombre de usuario es obligatorio."
        elif not password:
            error = "La contraseña es obligatoria."
        elif not selected_role_code:
            error = "El rol es obligatorio."

        if error is None:
            try:
                # Insert user into 'users' table
                user_id = db.execute(
                    "INSERT INTO users (username, email, password_hash, nombre, apellidos, telefono, direccion, ciudad, provincia, cp, nif, whatsapp_number, whatsapp_opt_in, costo_por_hora, tasa_recargo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        username,
                        email,
                        generate_password_hash(password),
                        nombre,
                        apellidos,
                        telefono,
                        direccion,
                        ciudad,
                        provincia,
                        cp,
                        nif,
                        whatsapp_number,
                        whatsapp_opt_in,
                        costo_por_hora,
                        tasa_recargo,
                    ),  # Updated
                ).lastrowid

                # Get role ID and insert into 'user_roles' table
                role_row = db.execute(
                    "SELECT id FROM roles WHERE code = ?", (selected_role_code,)
                ).fetchone()
                if role_row:
                    db.execute(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                        (user_id, role_row["id"]),
                    )

                db.commit()
                flash(f"¡Usuario {username} creado correctamente!")
                return redirect(url_for("users.list_users"))
            except sqlite3.IntegrityError:
                error = f"El usuario {username} o el email {email} ya existen."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"

            if error:
                flash(error)

    roles = db.execute(
        "SELECT code, descripcion FROM roles ORDER BY descripcion"
    ).fetchall()
    # Pass user=None to indicate we are creating, not editing
    return render_template(
        "users/form.html", roles=roles, user=None, user_current_role_code=None
    )


@bp.route("/<int:user_id>/edit", methods=("GET", "POST"))
@login_required
def edit_user(user_id):
    db = get_db()
    if db is None:
        flash("Database connection error.", "error")
        return redirect(url_for("users.list_users"))
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if user is None:
        flash("Usuario no encontrado.")
        return redirect(url_for("users.list_users"))

    roles = db.execute(
        "SELECT code, descripcion FROM roles ORDER BY descripcion"
    ).fetchall()

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form.get("password")
        nombre = request.form["nombre"]
        apellidos = request.form["apellidos"]
        telefono = request.form["telefono"]
        direccion = request.form["direccion"]
        ciudad = request.form["ciudad"]
        provincia = request.form["provincia"]
        cp = request.form["cp"]
        nif = request.form["nif"]
        selected_role_code = request.form[
            "role"
        ]  # Assuming role is selected from dropdown
        whatsapp_number = request.form.get("whatsapp_number")
        whatsapp_opt_in = "whatsapp_opt_in" in request.form  # Checkbox value
        costo_por_hora = request.form.get(
            "costo_por_hora", type=float, default=0.0
        )  # New
        tasa_recargo = request.form.get("tasa_recargo", type=float, default=0.0)  # New
        error = None
        if not username:
            error = "El nombre de usuario es obligatorio."
        elif not selected_role_code:
            error = "El rol es obligatorio."

        if error is not None:
            flash(error)
        else:
            try:
                # Update user details in 'users' table
                if password:
                    db.execute(
                        "UPDATE users SET username = ?, email = ?, password_hash = ?, nombre = ?, apellidos = ?, telefono = ?, direccion = ?, ciudad = ?, provincia = ?, cp = ?, nif = ?, whatsapp_number = ?, whatsapp_opt_in = ?, costo_por_hora = ?, tasa_recargo = ? WHERE id = ?",
                        (
                            username,
                            email,
                            generate_password_hash(password),
                            nombre,
                            apellidos,
                            telefono,
                            direccion,
                            ciudad,
                            provincia,
                            cp,
                            nif,
                            whatsapp_number,
                            whatsapp_opt_in,
                            costo_por_hora,
                            tasa_recargo,
                            user_id,
                        ),  # Updated
                    )
                else:
                    db.execute(
                        "UPDATE users SET username = ?, email = ?, nombre = ?, apellidos = ?, telefono = ?, direccion = ?, ciudad = ?, provincia = ?, cp = ?, nif = ?, whatsapp_number = ?, whatsapp_opt_in = ?, costo_por_hora = ?, tasa_recargo = ? WHERE id = ?",
                        (
                            username,
                            email,
                            nombre,
                            apellidos,
                            telefono,
                            direccion,
                            ciudad,
                            provincia,
                            cp,
                            nif,
                            whatsapp_number,
                            whatsapp_opt_in,
                            costo_por_hora,
                            tasa_recargo,
                            user_id,
                        ),  # Updated
                    )

                # Update user roles in 'user_roles' table
                # First, delete existing roles for this user
                db.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))

                # Then, insert the new role
                role_row = db.execute(
                    "SELECT id FROM roles WHERE code = ?", (selected_role_code,)
                ).fetchone()
                if role_row:
                    selected_role_id = role_row["id"]
                    db.execute(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                        (user_id, selected_role_id),
                    )
                else:
                    # This case should ideally not happen if the form is populated correctly,
                    # but as a safeguard, we prevent the crash and prepare an error message.
                    error = f"El rol '{selected_role_code}' seleccionado no es válido."

                db.commit()
                flash("¡Usuario actualizado correctamente!")
                return redirect(url_for("users.list_users"))
            except sqlite3.IntegrityError:
                error = f"El usuario {username} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"

            if error:
                flash(error)

    # For GET request or if POST fails, fetch current user's roles for display
    user_current_role_code = db.execute(
        "SELECT r.code FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = ?",
        (user_id,),
    ).fetchone()
    if user_current_role_code:
        user_current_role_code = user_current_role_code["code"]
    else:
        user_current_role_code = None  # No role assigned or found

    return render_template(
        "users/form.html",
        user=user,
        roles=roles,
        user_current_role_code=user_current_role_code,
    )


@bp.route("/<int:user_id>/delete", methods=("POST",))
@login_required
def delete_user(user_id):
    db = get_db()
    if db is None:
        flash("Database connection error.", "error")
        return redirect(url_for("users.list_users"))

    try:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.execute(
            "DELETE FROM user_roles WHERE user_id = ?", (user_id,)
        )  # Also delete from user_roles
        db.commit()
        flash("¡Usuario eliminado correctamente!")
    except Exception as e:
        flash(f"Error deleting user: {e}", "error")
        db.rollback()

    return redirect(url_for("users.list_users"))
