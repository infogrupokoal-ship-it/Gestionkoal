import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3
from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('services', __name__, url_prefix='/services')

@bp.route('/')
@login_required
def list_services():
    db = get_db()
    services = db.execute(
        'SELECT id, name, description, price, recommended_price, last_sold_price, category FROM services ORDER BY name'
    ).fetchall()
    return render_template('services/list.html', services=services)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_service():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form.get('price')
        precio_base = request.form.get('precio_base', type=float, default=0.0)
        db = get_db()
        error = None

        if not name:
            error = 'El nombre es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'INSERT INTO services (name, description, price, precio_base) VALUES (?, ?, ?, ?)',
                    (name, description, price, precio_base)
                )
                db.commit()
                flash('¡Servicio añadido correctamente!')
                return redirect(url_for('services.list_services'))
            except sqlite3.IntegrityError:
                error = f"El servicio {name} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('services/form.html', service=None)

@bp.route('/<int:service_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_service(service_id):
    db = get_db()
    service = db.execute('SELECT id, name, description, price, recommended_price, last_sold_price, category, precio_base FROM services WHERE id = ?', (service_id,)).fetchone()

    if service is None:
        flash('Servicio no encontrado.')
        return redirect(url_for('services.list_services'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        recommended_price = request.form.get('recommended_price')
        last_sold_price = request.form.get('last_sold_price')
        category = request.form.get('category')
        precio_base = request.form.get('precio_base', type=float, default=0.0)
        error = None

        if not name:
            error = 'El nombre es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'UPDATE services SET name = ?, description = ?, price = ?, recommended_price = ?, last_sold_price = ?, category = ?, precio_base = ? WHERE id = ?',
                    (name, description, price, recommended_price, last_sold_price, category, precio_base, service_id)
                )
                db.commit()
                flash('¡Servicio actualizado correctamente!')
                return redirect(url_for('services.list_services'))
            except sqlite3.IntegrityError:
                error = f"El servicio {name} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('services/form.html', service=service)