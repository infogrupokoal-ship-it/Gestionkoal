import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('financial_transactions', __name__, url_prefix='/financial_transactions')

@bp.route('/')
@login_required
def list_transactions():
    db = get_db()
    transactions = db.execute(
        '''SELECT ft.id, ft.descripcion, ft.monto, ft.tipo, ft.fecha, u.username as creado_por_username
           FROM financial_transactions ft JOIN users u ON ft.creado_por = u.id ORDER BY ft.fecha DESC'''
    ).fetchall()
    return render_template('financial_transactions/list.html', transactions=transactions)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_transaction():
    db = get_db()
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        monto = request.form.get('monto', type=float)
        tipo = request.form.get('tipo')
        fecha = request.form.get('fecha')
        pagado_por = request.form.get('pagado_por', type=int)
        error = None

        if not descripcion or not monto or not tipo or not fecha:
            error = 'Descripción, monto, tipo y fecha son obligatorios.'
        if monto <= 0:
            error = 'El monto debe ser un número positivo.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''INSERT INTO financial_transactions (descripcion, monto, tipo, fecha, creado_por, pagado_por)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (descripcion, monto, tipo, fecha, g.user.id, pagado_por)
                )
                db.commit()
                flash('¡Transacción añadida correctamente!')
                return redirect(url_for('financial_transactions.list_transactions'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('financial_transactions/form.html', transaction=None, users=users)
