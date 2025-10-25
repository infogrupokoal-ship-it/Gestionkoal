import json

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.db_utils import get_db

bp = Blueprint('shared_expenses', __name__, url_prefix='/shared_expenses')

@bp.route('/')
@login_required
def list_shared_expenses():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    expenses = db.execute(
        '''SELECT se.id, se.descripcion, se.monto, se.fecha, u.username as creado_por_username, se.estado
           FROM gastos_compartidos se JOIN users u ON se.creado_por = u.id ORDER BY se.fecha DESC'''
    ).fetchall()
    return render_template('shared_expenses/list.html', expenses=expenses)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_shared_expense():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('shared_expenses.list_shared_expenses'))
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        monto = request.form.get('monto', type=float)
        fecha = request.form.get('fecha')
        pagado_por = request.form.get('pagado_por', type=int)
        participantes_raw = request.form.getlist('participantes') # Get list of selected user IDs
        error = None

        if not descripcion or not monto or not fecha:
            error = 'Descripción, monto y fecha son obligatorios.'
        if monto <= 0:
            error = 'El monto debe ser un número positivo.'
        if not pagado_por:
            error = 'Debe seleccionar quién pagó el gasto.'
        if not participantes_raw:
            error = 'Debe seleccionar al menos un participante.'

        if error is not None:
            flash(error)
        else:
            try:
                participantes_json = json.dumps([int(uid) for uid in participantes_raw])
                db.execute(
                    '''INSERT INTO gastos_compartidos (descripcion, monto, fecha, creado_por, pagado_por, participantes, estado)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (descripcion, monto, fecha, g.user.id, pagado_por, participantes_json, 'pendiente')
                )
                db.commit()
                flash('¡Gasto compartido añadido correctamente!')
                return redirect(url_for('shared_expenses.list_shared_expenses'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('shared_expenses/form.html', expense=None, users=users)
