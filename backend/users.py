import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from werkzeug.security import generate_password_hash, check_password_hash

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
@login_required
def list_users():
    db = get_db()
    users = db.execute(
        '''
        SELECT
            u.id, u.username, u.email, u.nombre, u.telefono, u.nif,
            GROUP_CONCAT(r.code) AS roles_codes
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        LEFT JOIN roles r ON ur.role_id = r.id
        GROUP BY u.id, u.username, u.email, u.nombre, u.telefono, u.nif
        ORDER BY u.username
        '''
    ).fetchall()
    return render_template('users/list.html', users=users)

@bp.route('/<int:user_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_user(user_id):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if user is None:
        flash('Usuario no encontrado.')
        return redirect(url_for('users.list_users'))

    roles = db.execute('SELECT id, code, descripcion FROM roles').fetchall()

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form.get('password')
        selected_role_code = request.form['role'] # Assuming role is selected from dropdown
        error = None

        if not username:
            error = 'El nombre de usuario es obligatorio.'
        elif not selected_role_code:
            error = 'El rol es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                # Update user details in 'users' table
                if password:
                    db.execute(
                        'UPDATE users SET username = ?, email = ?, password_hash = ? WHERE id = ?',
                        (username, email, generate_password_hash(password), user_id)
                    )
                else:
                    db.execute(
                        'UPDATE users SET username = ?, email = ? WHERE id = ?',
                        (username, email, user_id)
                    )
                
                # Update user roles in 'user_roles' table
                # First, delete existing roles for this user
                db.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
                
                # Then, insert the new role
                selected_role_id = db.execute('SELECT id FROM roles WHERE code = ?', (selected_role_code,)).fetchone()['id']
                db.execute('INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)', (user_id, selected_role_id))
                
                db.commit()
                flash('¡Usuario actualizado correctamente!')
                return redirect(url_for('users.list_users'))
            except sqlite3.IntegrityError:
                error = f"El usuario {username} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    # For GET request or if POST fails, fetch current user's roles for display
    user_current_role_code = db.execute('SELECT r.code FROM user_roles ur JOIN roles r ON ur.role_id = r.id WHERE ur.user_id = ?', (user_id,)).fetchone()
    if user_current_role_code:
        user_current_role_code = user_current_role_code['code']
    else:
        user_current_role_code = None # No role assigned or found

    return render_template('users/form.html', user=user, roles=roles, user_current_role_code=user_current_role_code)

@bp.route('/<int:user_id>/delete', methods=('POST',))
@login_required
def delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,)) # Also delete from user_roles
    db.commit()
    flash('¡Usuario eliminado correctamente!')
    return redirect(url_for('users.list_users'))
