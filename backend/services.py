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

@bp.route('/<int:service_id>')
@login_required
def view_service(service_id):
    db = get_db()
    service = db.execute(
        'SELECT * FROM services WHERE id = ?',
        (service_id,)
    ).fetchone()

    if service is None:
        flash('Servicio no encontrado.', 'error')
        return redirect(url_for('services.list_services'))

    return render_template('services/view.html', service=service)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_service():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        recommended_price = request.form.get('recommended_price')
        last_sold_price = request.form.get('last_sold_price')
        category = request.form.get('category')
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
                    'INSERT INTO services (name, description, price, recommended_price, last_sold_price, category, precio_base) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (name, description, price, recommended_price, last_sold_price, category, precio_base)
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

        # Fetch market study data for the service (if available)
        market_study_data = db.execute(
            "SELECT precio_recomendado FROM estudio_mercado WHERE tipo_elemento = 'servicio' AND elemento_id = ? ORDER BY fecha_estudio DESC LIMIT 1",
            (service_id,)
        ).fetchone()

        if market_study_data:
            suggested_price_from_market = market_study_data['precio_recomendado']
            # If price is not provided by user, use suggested price from market study
            if price is None or price == '':
                price = suggested_price_from_market
            # If precio_base is not provided by user, use suggested price from market study
            if precio_base is None or precio_base == 0.0:
                precio_base = suggested_price_from_market

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