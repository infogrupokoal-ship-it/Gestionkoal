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
        'SELECT id, nombre, tipo, estado, ubicacion FROM activos ORDER BY nombre'
    ).fetchall()
    return render_template('asset_management/assets_list.html', assets=assets)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_asset():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        tipo = request.form.get('tipo')
        descripcion = request.form.get('descripcion')
        costo_adquisicion = request.form.get('costo_adquisicion', type=float)
        fecha_adquisicion = request.form.get('fecha_adquisicion')
        estado = request.form.get('estado')
        ubicacion = request.form.get('ubicacion')
        error = None

        if not nombre or not tipo or not estado:
            error = 'Nombre, tipo y estado son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db = get_db()
                db.execute(
                    '''INSERT INTO activos (nombre, tipo, descripcion, costo_adquisicion, fecha_adquisicion, estado, ubicacion)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (nombre, tipo, descripcion, costo_adquisicion, fecha_adquisicion, estado, ubicacion)
                )
                db.commit()
                flash('¡Activo añadido correctamente!')
                return redirect(url_for('asset_management.list_assets'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('asset_management/asset_form.html', asset=None)

@bp.route('/<int:asset_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_asset(asset_id):
    db = get_db()
    asset = db.execute('SELECT * FROM activos WHERE id = ?', (asset_id,)).fetchone()

    if asset is None:
        flash('Activo no encontrado.')
        return redirect(url_for('asset_management.list_assets'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        tipo = request.form.get('tipo')
        descripcion = request.form.get('descripcion')
        costo_adquisicion = request.form.get('costo_adquisicion', type=float)
        fecha_adquisicion = request.form.get('fecha_adquisicion')
        estado = request.form.get('estado')
        ubicacion = request.form.get('ubicacion')
        error = None

        if not nombre or not tipo or not estado:
            error = 'Nombre, tipo y estado son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE activos SET 
                       nombre = ?, tipo = ?, descripcion = ?, costo_adquisicion = ?, 
                       fecha_adquisicion = ?, estado = ?, ubicacion = ?
                       WHERE id = ?''',
                    (nombre, tipo, descripcion, costo_adquisicion, fecha_adquisicion, estado, ubicacion, asset_id)
                )
                db.commit()
                flash('¡Activo actualizado correctamente!')
                return redirect(url_for('asset_management.list_assets'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('asset_management/asset_form.html', asset=asset)

@bp.route('/loans')
@login_required
def list_loans():
    db = get_db()
    loans = db.execute(
        '''SELECT pl.id, a.nombre as activo_nombre, u.username as usuario_nombre, pl.fecha_inicio, pl.fecha_fin_prevista, pl.estado
           FROM prestamos_alquileres pl JOIN activos a ON pl.activo_id = a.id JOIN users u ON pl.usuario_id = u.id ORDER BY pl.fecha_inicio DESC'''
    ).fetchall()
    return render_template('asset_management/loans_list.html', loans=loans)

@bp.route('/loans/add', methods=('GET', 'POST'))
@login_required
def add_loan():
    db = get_db()
    assets = db.execute('SELECT id, nombre, tipo FROM activos ORDER BY nombre').fetchall()
    users = db.execute('SELECT id, username FROM users ORDER BY username').fetchall()

    if request.method == 'POST':
        activo_id = request.form.get('activo_id', type=int)
        usuario_id = request.form.get('usuario_id', type=int)
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin_prevista = request.form.get('fecha_fin_prevista')
        costo_alquiler = request.form.get('costo_alquiler', type=float, default=0.0)
        estado = request.form.get('estado')
        notas = request.form.get('notas')
        error = None

        if not activo_id or not usuario_id or not fecha_inicio or not fecha_fin_prevista:
            error = 'Activo, usuario, fecha de inicio y fecha fin prevista son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''INSERT INTO prestamos_alquileres (activo_id, usuario_id, fecha_inicio, fecha_fin_prevista, costo_alquiler, estado, notas)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (activo_id, usuario_id, fecha_inicio, fecha_fin_prevista, costo_alquiler, estado, notas)
                )
                db.commit()
                flash('¡Préstamo/Alquiler añadido correctamente!')
                return redirect(url_for('asset_management.list_loans'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('asset_management/loan_form.html', loan=None, assets=assets, users=users)
