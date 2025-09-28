import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('catalog', __name__, url_prefix='/catalog')

@bp.route('/')
def public_list():
    db = get_db()
    services = db.execute(
        'SELECT id, name, description, price, category FROM services ORDER BY name'
    ).fetchall()
    return render_template('catalog/public_list.html', services=services)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_service():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float)
        category = request.form.get('category')
        error = None

        if not name or not price:
            error = 'Nombre y precio son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'INSERT INTO services (name, description, price, category) VALUES (?, ?, ?, ?)',
                    (name, description, price, category)
                )
                db.commit()
                flash('¡Servicio añadido correctamente!')
                return redirect(url_for('catalog.public_list'))
            except sqlite3.IntegrityError:
                error = f"El servicio {name} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('catalog/form.html', title="Añadir Servicio", service=None)

@bp.route('/<int:service_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_service(service_id):
    db = get_db()
    service = db.execute('SELECT id, name, description, price, category FROM services WHERE id = ?', (service_id,)).fetchone()

    if service is None:
        flash('Servicio no encontrado.')
        return redirect(url_for('catalog.public_list'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price', type=float)
        category = request.form.get('category')
        error = None

        if not name or not price:
            error = 'Nombre y precio son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'UPDATE services SET name = ?, description = ?, price = ?, category = ? WHERE id = ?',
                    (name, description, price, category, service_id)
                )
                db.commit()
                flash('¡Servicio actualizado correctamente!')
                return redirect(url_for('catalog.public_list'))
            except sqlite3.IntegrityError:
                error = f"El servicio {name} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('catalog/form.html', title="Editar Servicio", service=service)

@bp.route('/<int:service_id>/delete', methods=('POST',))
@login_required
def delete_service(service_id):
    db = get_db()
    db.execute('DELETE FROM services WHERE id = ?', (service_id,))
    db.commit()
    flash('¡Servicio eliminado correctamente!')
    return redirect(url_for('catalog.public_list'))

@bp.route('/view/<int:service_id>')
def view_service(service_id):
    db = get_db()
    service = db.execute(
        'SELECT id, name, description, price, category FROM services WHERE id = ?',
        (service_id,)
    ).fetchone()

    if service is None:
        flash('Servicio no encontrado.')
        return redirect(url_for('catalog.public_list'))

    return render_template('catalog/view_service.html', service=service)
