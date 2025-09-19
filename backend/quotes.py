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

        # Recopilar y validar ítems
        for i in range(3):
            descripcion = request.form.get(f'item_descripcion_{i}')
            qty_str = request.form.get(f'item_qty_{i}')
            precio_unit_str = request.form.get(f'item_precio_unit_{i}')

            if not descripcion and (not qty_str or not precio_unit_str):
                continue # Ignorar líneas vacías

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
