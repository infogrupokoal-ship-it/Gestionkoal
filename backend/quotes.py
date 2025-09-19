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
        estado = request.form.get('estado')
        total = 0.0
        items_data = []
        error = None

        descripciones = request.form.getlist('item_descripcion[]')
        quantities = request.form.getlist('item_qty[]')
        unit_prices = request.form.getlist('item_precio_unit[]')

        # Recopilar y validar ítems
        for i in range(len(descripciones)):
            descripcion = descripciones[i].strip()
            qty_str = quantities[i].strip()
            precio_unit_str = unit_prices[i].strip()

            if not descripcion and (not qty_str or not precio_unit_str):
                continue # Ignorar líneas completamente vacías

            try:
                qty = float(qty_str) if qty_str else 0.0
                precio_unit = float(precio_unit_str) if precio_unit_str else 0.0
            except ValueError:
                error = 'Cantidad y Precio Unitario deben ser números válidos.'
                break
            
            if not descripcion:
                error = 'La descripción del ítem no puede estar vacía si hay cantidad o precio.'
                break

            item_total = qty * precio_unit
            total += item_total
            items_data.append({
                'descripcion': descripcion,
                'qty': qty,
                'precio_unit': precio_unit
            })
        
        if error is not None:
            flash(error)
        elif not items_data:
            flash('Debe añadir al menos un ítem al presupuesto.')
        else:
            try:
                # Insertar Presupuesto principal
                cursor = db.execute(
                    'INSERT INTO presupuestos (ticket_id, estado, total) VALUES (?, ?, ?)',
                    (trabajo_id, estado, total)
                )
                presupuesto_id = cursor.lastrowid

                # Insertar ítems del Presupuesto
                for item in items_data:
                    db.execute(
                        'INSERT INTO presupuesto_items (presupuesto_id, descripcion, qty, precio_unit) VALUES (?, ?, ?, ?)',
                        (presupuesto_id, item['descripcion'], item['qty'], item['precio_unit'])
                    )
                
                db.commit()
                flash('¡Presupuesto creado correctamente!')
                return redirect(url_for('jobs.edit_job', job_id=trabajo_id)) # Redirigir de vuelta al trabajo

            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error al guardar el presupuesto: {e}"
                flash(error)

    return render_template('quotes/form.html', trabajo=trabajo)

@bp.route('/<int:quote_id>/view', methods=('GET', 'POST'))
@login_required
def view_quote(quote_id):
    db = get_db()
    presupuesto = db.execute('SELECT * FROM presupuestos WHERE id = ?', (quote_id,)).fetchone()

    if presupuesto is None:
        flash('Presupuesto no encontrado.')
        return redirect(url_for('jobs.list_jobs')) # Redirigir a la lista de trabajos o a una lista de presupuestos

    # Fetch items for the quote
    items = db.execute(
        'SELECT id, descripcion, qty, precio_unit FROM presupuesto_items WHERE presupuesto_id = ?',
        (quote_id,)
    ).fetchall()

    if request.method == 'POST':
        estado = request.form.get('estado')
        total = 0.0
        items_to_process = []
        error = None

        item_ids = request.form.getlist('item_id[]')
        descripciones = request.form.getlist('item_descripcion[]')
        quantities = request.form.getlist('item_qty[]')
        unit_prices = request.form.getlist('item_precio_unit[]')

        # Recopilar y validar ítems
        for i in range(len(descripciones)):
            item_id_str = item_ids[i].strip()
            descripcion = descripciones[i].strip()
            qty_str = quantities[i].strip()
            precio_unit_str = unit_prices[i].strip()

            # Si la descripción está vacía y no hay ID, es una fila vacía que ignoramos
            if not descripcion and not item_id_str and (not qty_str or not precio_unit_str):
                continue

            try:
                qty = float(qty_str) if qty_str else 0.0
                precio_unit = float(precio_unit_str) if precio_unit_str else 0.0
            except ValueError:
                error = 'Cantidad y Precio Unitario deben ser números válidos.'
                break
            
            if not descripcion:
                error = 'La descripción del ítem no puede estar vacía si hay cantidad o precio.'
                break

            item_total = qty * precio_unit
            total += item_total
            items_to_process.append({
                'id': int(item_id_str) if item_id_str else None,
                'descripcion': descripcion,
                'qty': qty,
                'precio_unit': precio_unit
            })
        
        if error is not None:
            flash(error)
        elif not items_to_process:
            flash('Debe añadir al menos un ítem al presupuesto.')
        else:
            try:
                # Actualizar Presupuesto principal
                db.execute(
                    'UPDATE presupuestos SET estado = ?, total = ? WHERE id = ?',
                    (estado, total, quote_id)
                )

                # Obtener IDs de ítems existentes para detectar eliminaciones
                existing_item_ids = [item['id'] for item in items if item['id'] is not None]
                submitted_item_ids = [item['id'] for item in items_to_process if item['id'] is not None]

                # Eliminar ítems que ya no están en el formulario
                for existing_id in existing_item_ids:
                    if existing_id not in submitted_item_ids:
                        db.execute('DELETE FROM presupuesto_items WHERE id = ?', (existing_id,))

                # Actualizar/Insertar ítems
                for item in items_to_process:
                    if item['id']:
                        # Actualizar ítem existente
                        db.execute(
                            'UPDATE presupuesto_items SET descripcion = ?, qty = ?, precio_unit = ? WHERE id = ?',
                            (item['descripcion'], item['qty'], item['precio_unit'], item['id'])
                        )
                    else:
                        # Insertar nuevo ítem
                        db.execute(
                            'INSERT INTO presupuesto_items (presupuesto_id, descripcion, qty, precio_unit) VALUES (?, ?, ?, ?)',
                            (quote_id, item['descripcion'], item['qty'], item['precio_unit'])
                        )
                
                db.commit()
                flash('¡Presupuesto actualizado correctamente!')
                return redirect(url_for('quotes.view_quote', quote_id=quote_id))

            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error al actualizar el presupuesto: {e}"
                flash(error)

    return render_template('quotes/view.html', presupuesto=presupuesto, items=items)

@bp.route('/<int:quote_id>/delete', methods=('POST',))
@login_required
def delete_quote(quote_id):
    db = get_db()
    presupuesto = db.execute('SELECT id FROM presupuestos WHERE id = ?', (quote_id,)).fetchone()

    if presupuesto is None:
        flash('Presupuesto no encontrado.')
        return redirect(url_for('jobs.list_jobs')) # O a la lista de presupuestos

    try:
        # Eliminar ítems del presupuesto
        db.execute('DELETE FROM presupuesto_items WHERE presupuesto_id = ?', (quote_id,))
        # Eliminar el presupuesto principal
        db.execute('DELETE FROM presupuestos WHERE id = ?', (quote_id,))
        db.commit()
        flash('¡Presupuesto eliminado correctamente!')
    except Exception as e:
        db.rollback()
        flash(f'Ocurrió un error al eliminar el presupuesto: {e}')
    
    return redirect(url_for('jobs.list_jobs')) # Redirigir a la lista de trabajos

