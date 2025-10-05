from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('services', __name__, url_prefix='/services')

@bp.route('/')
@login_required
def list_services():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    services = db.execute('SELECT id, name, description, price, category FROM services').fetchall()
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
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('services.list_services'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']
        error = None

        if not name:
            error = 'Name is required.'
        elif not price:
            error = 'Price is required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO services (name, description, price, category) VALUES (?, ?, ?, ?)",
                    (name, description, price, category),
                )
                db.commit()
                flash('Service added successfully.', 'success')
                return redirect(url_for('services.list_services'))
            except db.IntegrityError:
                error = f"Service {name} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    return render_template('services/add.html')

@bp.route('/<int:service_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_service(service_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('services.list_services'))

    service = db.execute(
        'SELECT id, name, description, price, category FROM services WHERE id = ?',
        (service_id,)
    ).fetchone()

    if service is None:
        flash('Service not found.', 'error')
        return redirect(url_for('services.list_services'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']
        error = None

        if not name:
            error = 'Name is required.'
        elif not price:
            error = 'Price is required.'

        if error is None:
            try:
                db.execute(
                    "UPDATE services SET name = ?, description = ?, price = ?, category = ? WHERE id = ?",
                    (name, description, price, category, service_id),
                )
                db.commit()
                flash('Service updated successfully.', 'success')
                return redirect(url_for('services.list_services'))
            except db.IntegrityError:
                error = f"Service {name} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    return render_template('services/edit.html', service=service)

@bp.route('/<int:service_id>/delete', methods=('POST',))
@login_required
def delete_service(service_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('services.list_services'))

    try:
        db.execute('DELETE FROM services WHERE id = ?', (service_id,))
        db.commit()
        flash('Service deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting service: {e}', 'error')
        db.rollback()

    return redirect(url_for('services.list_services'))