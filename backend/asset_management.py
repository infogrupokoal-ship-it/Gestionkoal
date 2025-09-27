import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('asset_management', __name__, url_prefix='/assets')

@bp.route('/')
@login_required
def list_assets():
    db = get_db()
    assets = db.execute(
        'SELECT id, nombre, codigo, estado, observaciones FROM herramientas ORDER BY nombre'
    ).fetchall()
    return render_template('asset_management/assets_list.html', assets=assets)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_asset():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        # Map 'tipo' from form to 'codigo' in DB
        codigo = request.form.get('tipo') 
        # Map 'descripcion' from form to 'observaciones' in DB
        observaciones = request.form.get('descripcion')
        estado = request.form.get('estado')
        error = None

        # 'codigo' is the new 'tipo'
        if not nombre or not codigo or not estado:
            error = 'Nombre, Código (Tipo) y Estado son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db = get_db()
                db.execute(
                    '''INSERT INTO herramientas (nombre, codigo, observaciones, estado)
                       VALUES (?, ?, ?, ?)''',
                    (nombre, codigo, observaciones, estado)
                )
                db.commit()
                flash('¡Herramienta/Activo añadido correctamente!')
                return redirect(url_for('asset_management.list_assets'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('asset_management/asset_form.html', asset=None)

@bp.route('/<int:asset_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_asset(asset_id):
    db = get_db()
    asset = db.execute('SELECT * FROM herramientas WHERE id = ?', (asset_id,)).fetchone()

    if asset is None:
        flash('Herramienta/Activo no encontrado.')
        return redirect(url_for('asset_management.list_assets'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        codigo = request.form.get('tipo') # Remap
        observaciones = request.form.get('descripcion') # Remap
        estado = request.form.get('estado')
        error = None

        if not nombre or not codigo or not estado:
            error = 'Nombre, Código (Tipo) y Estado son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE herramientas SET 
                       nombre = ?, codigo = ?, observaciones = ?, estado = ?
                       WHERE id = ?''',
                    (nombre, codigo, observaciones, estado, asset_id)
                )
                db.commit()
                flash('¡Herramienta/Activo actualizado correctamente!')
                return redirect(url_for('asset_management.list_assets'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('asset_management/asset_form.html', asset=asset)

@bp.route('/loans')
@login_required
def list_loans():
    db = get_db()
    # Corrected query for 'prestamos_herramienta'
    loans = db.execute(
        '''SELECT p.id, h.nombre as activo_nombre, u.username as usuario_nombre, p.salida as fecha_inicio, p.devolucion as fecha_fin_prevista, p.estado_salida as estado
           FROM prestamos_herramienta p JOIN herramientas h ON p.herramienta_id = h.id JOIN users u ON p.usuario_id = u.id ORDER BY p.salida DESC'''
    ).fetchall()
    return render_template('asset_management/loans_list.html', loans=loans)

@bp.route('/loans/add', methods=('GET', 'POST'))
@login_required
def add_loan():
    db = get_db()
    # Corrected query for assets -> herramientas
    assets = db.execute('SELECT id, nombre FROM herramientas ORDER BY nombre').fetchall()
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()

    if request.method == 'POST':
        herramienta_id = request.form.get('activo_id', type=int) # Form still uses 'activo_id'
        usuario_id = request.form.get('usuario_id', type=int)
        salida = request.form.get('fecha_inicio')
        devolucion = request.form.get('fecha_fin_prevista')
        estado_salida = request.form.get('estado')
        observaciones = request.form.get('notas')
        error = None

        if not herramienta_id or not usuario_id or not salida:
            error = 'Herramienta, usuario y fecha de inicio son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''INSERT INTO prestamos_herramienta (herramienta_id, usuario_id, salida, devolucion, estado_salida, observaciones)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (herramienta_id, usuario_id, salida, devolucion, estado_salida, observaciones)
                )
                db.commit()
                flash('¡Préstamo de herramienta añadido correctamente!')
                return redirect(url_for('asset_management.list_loans'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('asset_management/loan_form.html', loan=None, assets=assets, users=users)

@bp.route('/loans/<int:loan_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_loan(loan_id):
    db = get_db()
    loan = db.execute('SELECT * FROM prestamos_herramienta WHERE id = ?', (loan_id,)).fetchone()

    if loan is None:
        flash('Préstamo de herramienta no encontrado.')
        return redirect(url_for('asset_management.list_loans'))

    assets = db.execute('SELECT id, nombre FROM herramientas ORDER BY nombre').fetchall()
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()

    if request.method == 'POST':
        herramienta_id = request.form.get('activo_id', type=int)
        usuario_id = request.form.get('usuario_id', type=int)
        salida = request.form.get('fecha_inicio')
        devolucion = request.form.get('fecha_fin_prevista')
        estado_salida = request.form.get('estado')
        estado_entrada = request.form.get('estado_entrada') # Assuming form might have this
        observaciones = request.form.get('notas')
        error = None

        if not herramienta_id or not usuario_id or not salida:
            error = 'Herramienta, usuario y fecha de inicio son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE prestamos_herramienta SET 
                       herramienta_id = ?, usuario_id = ?, salida = ?, devolucion = ?, 
                       estado_salida = ?, estado_entrada = ?, observaciones = ?
                       WHERE id = ?''',
                    (herramienta_id, usuario_id, salida, devolucion, estado_salida, estado_entrada, observaciones, loan_id)
                )
                db.commit()
                flash('¡Préstamo de herramienta actualizado correctamente!')
                return redirect(url_for('asset_management.list_loans'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('asset_management/loan_form.html', loan=loan, assets=assets, users=users)

@bp.route('/<int:asset_id>/delete', methods=('POST',))
@login_required
def delete_asset(asset_id):
    db = get_db()
    db.execute('DELETE FROM herramientas WHERE id = ?', (asset_id,))
    db.commit()
    flash('¡Herramienta/Activo eliminado correctamente!')
    return redirect(url_for('asset_management.list_assets'))

@bp.route('/loans/<int:loan_id>/delete', methods=('POST',))
@login_required
def delete_loan(loan_id):
    db = get_db()
    db.execute('DELETE FROM prestamos_herramienta WHERE id = ?', (loan_id,))
    db.commit()
    flash('¡Préstamo de herramienta eliminado correctamente!')
    return redirect(url_for('asset_management.list_loans'))
