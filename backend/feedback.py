import json

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import login_required

from backend.db import get_db

bp = Blueprint('feedback', __name__, url_prefix='/feedback')

@bp.route('/', methods=('GET', 'POST'))
@login_required
def feedback_form():
    if request.method == 'POST':
        description = request.form['description']
        steps = request.form['steps']
        contact = request.form['contact']
        error = None

        if not description:
            error = 'La descripción es obligatoria.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            if db is None:
                flash('Error de conexión a la base de datos.', 'error')
                return render_template('feedback/form.html')

            try:
                details = {
                    'steps': steps,
                    'contact': contact,
                    'user_id': g.user.id if g.user else None,
                    'username': g.user.username if g.user else 'Anonymous'
                }
                db.execute(
                    "INSERT INTO error_log (level, message, details) VALUES (?, ?, ?)",
                    ('feedback', description, json.dumps(details))
                )
                db.commit()
                flash('Tu feedback ha sido enviado. ¡Gracias!', 'success')
                return redirect(url_for('feedback.feedback_form'))
            except Exception as e:
                flash(f'Ocurrió un error al enviar el feedback: {e}', 'error')
                db.rollback()

    return render_template('feedback/form.html')
