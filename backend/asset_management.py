from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('asset_management', __name__, url_prefix='/assets')

@bp.route('/')
@login_required
def list_assets():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    assets = db.execute(
        'SELECT id, nombre, codigo, estado, observaciones FROM herramientas ORDER BY nombre'
    ).fetchall()
    return render_template('asset_management/assets_list.html', assets=assets)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_asset():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('asset_management.list_assets'))

    if request.method == 'POST':
        marca = request.form['marca']
        modelo = request.form['modelo']
        numero_serie = request.form['numero_serie']
        fecha_adquisicion = request.form['fecha_adquisicion']
        estado = request.form['estado']
        error = None

        if not marca or not modelo or not numero_serie:
            error = 'Marca, Modelo y Número de Serie son obligatorios.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO equipos (marca, modelo, numero_serie, fecha_adquisicion, estado) VALUES (?, ?, ?, ?, ?)",
                    (marca, modelo, numero_serie, fecha_adquisicion, estado),
                )
                db.commit()
                flash('Equipo añadido correctamente.', 'success')
                return redirect(url_for('asset_management.list_assets'))
            except db.IntegrityError:
                error = f"Equipo con número de serie {numero_serie} ya existe."
                db.rollback()
            except Exception as e:
                error = f"Ocurrió un error: {e}"
                db.rollback()

        flash(error)

    return render_template('asset_management/add.html')

@bp.route('/<int:asset_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_asset(asset_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('asset_management.list_assets'))

    asset = db.execute(
        'SELECT id, marca, modelo, numero_serie, fecha_adquisicion, estado FROM equipos WHERE id = ?',
        (asset_id,)
    ).fetchone()

    if asset is None:
        flash('Equipo no encontrado.', 'error')
        return redirect(url_for('asset_management.list_assets'))

    if request.method == 'POST':
        marca = request.form['marca']
        modelo = request.form['modelo']
        numero_serie = request.form['numero_serie']
        fecha_adquisicion = request.form['fecha_adquisicion']
        estado = request.form['estado']
        error = None

        if not marca or not modelo or not numero_serie:
            error = 'Marca, Modelo y Número de Serie son obligatorios.'

        if error is None:
            try:
                db.execute(
                    "UPDATE equipos SET marca = ?, modelo = ?, numero_serie = ?, fecha_adquisicion = ?, estado = ? WHERE id = ?",
                    (marca, modelo, numero_serie, fecha_adquisicion, estado, asset_id),
                )
                db.commit()
                flash('Equipo actualizado correctamente.', 'success')
                return redirect(url_for('asset_management.list_assets'))
            except db.IntegrityError:
                error = f"Equipo con número de serie {numero_serie} ya existe."
                db.rollback()
            except Exception as e:
                error = f"Ocurrió un error: {e}"
                db.rollback()

        flash(error)

    return render_template('asset_management/edit.html', asset=asset)

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
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('asset_management.list_assets'))

    try:
        db.execute('DELETE FROM equipos WHERE id = ?', (asset_id,))
        db.commit()
        flash('Equipo eliminado correctamente.', 'success')
    except Exception as e:
        flash(f'Error deleting asset: {e}', 'error')
        db.rollback()

    return redirect(url_for('asset_management.list_assets'))

@bp.route('/loans/<int:loan_id>/delete', methods=('POST',))
@login_required
def delete_loan(loan_id):
    db = get_db()
    db.execute('DELETE FROM prestamos_herramienta WHERE id = ?', (loan_id,))
    db.commit()
    flash('¡Préstamo de herramienta eliminado correctamente!')
    return redirect(url_for('asset_management.list_loans'))