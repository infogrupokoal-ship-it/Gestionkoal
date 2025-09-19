import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3
from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('quotes', __name__, url_prefix='/quotes')

@bp.route('/trabajos/<int:trabajo_id>/add', methods=('GET', 'POST'))
@login_required
def add_quote(trabajo_id):
    db = get_db()
    trabajo = db.execute('SELECT * FROM tickets WHERE id = ?', (trabajo_id,)).fetchone()

    if trabajo is None:
        flash('El trabajo no existe.')
        return redirect(url_for('jobs.list_jobs'))

    if request.method == 'POST':
        # Lógica para guardar el presupuesto y sus items irá aquí
        flash('Presupuesto guardado (funcionalidad en desarrollo).')
        return redirect(url_for('jobs.edit_job', job_id=trabajo_id))

    return render_template('quotes/form.html', trabajo=trabajo)
