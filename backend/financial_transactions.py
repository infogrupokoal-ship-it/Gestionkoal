from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.utils.permissions import require_permission
from backend.db_utils import get_db

bp = Blueprint('financial_transactions', __name__, url_prefix='/financial_transactions')

@bp.route('/')
@require_permission('view_reports')
def list_transactions():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    # Corrected to query 'gastos_compartidos' and its columns
    transactions = db.execute(
        '''SELECT gc.id, gc.descripcion, gc.monto, gc.fecha, u.username as creado_por_username, p.username as pagado_por_username
           FROM gastos_compartidos gc
           JOIN users u ON gc.creado_por = u.id
           LEFT JOIN users p ON gc.pagado_por = p.id
           ORDER BY gc.fecha DESC'''
    ).fetchall()
    return render_template('financial_transactions/list.html', transactions=transactions)

@bp.route('/add', methods=('GET', 'POST'))
@require_permission('manage_all_jobs')
def add_transaction():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('financial_transactions.list_transactions'))
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        monto = request.form.get('monto', type=float)
        # The 'tipo' field does not exist in 'gastos_compartidos', it's removed.
        fecha = request.form.get('fecha')
        pagado_por = request.form.get('pagado_por', type=int)
        # New fields from schema
        participantes = request.form.get('participantes') # Assuming a simple text field for now
        estado = request.form.get('estado', 'pendiente')

        error = None

        if not descripcion or not monto or not fecha:
            error = 'Descripción, monto y fecha son obligatorios.'

        if monto is not None and monto <= 0:
            error = 'El monto debe ser un número positivo.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    # Corrected to insert into 'gastos_compartidos'
                    '''INSERT INTO gastos_compartidos (descripcion, monto, fecha, creado_por, pagado_por, participantes, estado)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (descripcion, monto, fecha, g.user.id, pagado_por, participantes, estado)
                )
                db.commit()
                flash('¡Gasto añadido correctamente!')
                return redirect(url_for('financial_transactions.list_transactions'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('financial_transactions/form.html', transaction=None, users=users)
