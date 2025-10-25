import sqlite3

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.db_utils import get_db

bp = Blueprint('stock_movements', __name__, url_prefix='/stock_movements')

@bp.route('/')
@login_required
def list_stock_movements():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    movements = db.execute(
        '''SELECT sm.id, m.nombre as material_nombre, sm.qty, sm.motivo, sm.created_at, sm.costo_total, sm.estado_pago
           FROM stock_movs sm JOIN materiales m ON sm.material_id = m.id ORDER BY sm.created_at DESC'''
    ).fetchall()
    return render_template('stock_movements/list.html', movements=movements)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_movement():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('stock_movements.list_movements'))

    materials = db.execute('SELECT id, nombre, stock FROM materiales').fetchall()

    if request.method == 'POST':
        material_id = request.form['material_id']
        type = request.form['type']
        quantity = int(request.form['quantity'])
        error = None

        if not material_id or not type or not quantity:
            error = 'Material, Type, and Quantity are required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO stock_movements (material_id, type, quantity) VALUES (?, ?, ?)",
                    (material_id, type, quantity),
                )

                # Update material stock
                if type == 'entrada':
                    db.execute('UPDATE materiales SET stock = stock + ? WHERE id = ?', (quantity, material_id))
                elif type == 'salida':
                    db.execute('UPDATE materiales SET stock = stock - ? WHERE id = ?', (quantity, material_id))

                db.commit()
                flash('Stock movement added successfully.', 'success')
                return redirect(url_for('stock_movements.list_movements'))
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    return render_template('stock_movements/add.html', materials=materials)
    db = get_db()
    materials = db.execute('SELECT id, nombre FROM materiales ORDER BY nombre').fetchall()
    providers = db.execute('SELECT id, nombre FROM proveedores ORDER BY nombre').fetchall()

    if request.method == 'POST':
        material_id = request.form.get('material_id')
        qty = request.form.get('qty', type=float)
        motivo = request.form.get('motivo')
        origen = request.form.get('origen')
        destino = request.form.get('destino')
        costo_total = request.form.get('costo_total', type=float)
        fecha_pago = request.form.get('fecha_pago')
        estado_pago = request.form.get('estado_pago')
        proveedor_id = request.form.get('proveedor_id')
        usuario_id = g.user.id
        error = None

        if not material_id:
            error = 'Material es obligatorio.'
        if not qty or qty <= 0:
            error = 'Cantidad debe ser un número positivo.'
        if not motivo:
            error = 'Motivo es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                # Update material stock
                current_stock_row = db.execute('SELECT stock FROM materiales WHERE id = ?', (material_id,)).fetchone()
                current_stock = current_stock_row['stock'] if current_stock_row else 0

                new_stock = current_stock
                if motivo == 'compra' or motivo == 'ajuste_positivo':
                    new_stock += qty
                elif motivo == 'consumo_ticket' or motivo == 'ajuste_negativo':
                    new_stock -= qty
                # For 'traspaso', stock is updated in both origen/destino, handled separately if needed

                db.execute('UPDATE materiales SET stock = ? WHERE id = ?', (new_stock, material_id))

                # Insert stock movement record
                db.execute(
                    '''INSERT INTO stock_movs (material_id, qty, origen, destino, motivo, usuario_id, costo_total, fecha_pago, estado_pago, proveedor_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (material_id, qty, origen, destino, motivo, usuario_id, costo_total, fecha_pago, estado_pago, proveedor_id)
                )
                db.commit()
                flash('¡Movimiento de stock añadido correctamente!')
                return redirect(url_for('stock_movements.list_stock_movements'))
            except sqlite3.Error as e:
                db.rollback()
                error = f"Ocurrió un error en la base de datos: {e}"
                flash(error)
            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error inesperado: {e}"
                flash(error)

    return render_template('stock_movements/form.html', materials=materials, providers=providers, movement=None)
