import os

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('profile', __name__, url_prefix='/profile')

@bp.route('/')
@login_required
def user_profile():
    """Shows the profile information for the currently logged-in user."""
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login
    user_id = g.user.id

    # Fetch all user data, including the new avatar_url
    user_data = db.execute(
        'SELECT id, username, email, nombre, telefono, nif, avatar_url FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()

    # Fetch user roles
    user_roles = db.execute(
        '''SELECT r.code, r.descripcion
           FROM roles r JOIN user_roles ur ON r.id = ur.role_id
           WHERE ur.user_id = ?''',
        (user_id,)
    ).fetchall()

    if user_data is None:
        flash('Error: No se pudo encontrar el perfil del usuario.', 'error')
        return redirect(url_for('index'))

    return render_template('users/profile.html', user=user_data, roles=user_roles)

@bp.route('/edit', methods=('GET', 'POST'))
@login_required
def edit_profile():
    """Allows the currently logged-in user to edit their profile information."""
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login
    user_id = g.user.id

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        telefono = request.form.get('telefono')
        nif = request.form.get('nif')
        avatar_file = request.files.get('avatar')

        error = None
        avatar_url = g.user.avatar_url # Keep old avatar if none is uploaded

        if avatar_file and avatar_file.filename != '':
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            filename = secure_filename(avatar_file.filename)
            if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                # Create a user-specific filename to avoid conflicts
                filename = f'{user_id}_{filename}'
                avatar_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
                os.makedirs(avatar_folder, exist_ok=True)
                file_path = os.path.join(avatar_folder, filename)
                avatar_file.save(file_path)
                avatar_url = url_for('uploaded_file', filename=f'avatars/{filename}')
            else:
                error = 'Formato de imagen no válido. Permitidos: png, jpg, jpeg, gif.'

        if error is None:
            try:
                db.execute(
                    '''UPDATE users SET nombre = ?, email = ?, telefono = ?, nif = ?, avatar_url = ?
                       WHERE id = ?''',
                    (nombre, email, telefono, nif, avatar_url, user_id)
                )
                db.commit()
                flash('¡Perfil actualizado correctamente!')
                return redirect(url_for('profile.user_profile'))
            except db.IntegrityError:
                error = 'El email ya está en uso por otro usuario.'
                db.rollback()
            except Exception as e:
                error = f'Ocurrió un error inesperado: {e}'
                db.rollback()

        flash(error, 'error')

    return render_template('profile/edit_profile.html')
