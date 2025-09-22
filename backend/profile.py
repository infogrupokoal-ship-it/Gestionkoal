import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, url_for
)
from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('profile', __name__, url_prefix='/profile')

@bp.route('/')
@login_required
def user_profile():
    """
    Shows the profile information for the currently logged-in user.
    """
    db = get_db()
    
    # g.user is set by the load_logged_in_user function in auth.py
    # It should contain the full user record.
    user_id = g.user.id # Corrected: Use dot notation for object attribute

    # Fetch all user data from the 'users' table again to be sure
    user_data = db.execute(
        'SELECT id, username, email, nombre, telefono, nif FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()

    # Fetch user roles
    user_roles = db.execute(
        '''
        SELECT r.code, r.descripcion
        FROM roles r
        JOIN user_roles ur ON r.id = ur.role_id
        WHERE ur.user_id = ?
        ''',
        (user_id,)
    ).fetchall()

    if user_data is None:
        flash('Error: No se pudo encontrar el perfil del usuario.', 'error')
        return redirect(url_for('dashboard.index'))

    return render_template('users/profile.html', user=user_data, roles=user_roles)
