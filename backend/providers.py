from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('providers', __name__, url_prefix='/proveedores')

@bp.route('/')
@login_required
def list_providers():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    providers = db.execute('SELECT id, nombre, telefono, email, tipo_proveedor FROM providers').fetchall()
    return render_template('proveedores/list.html', providers=providers)

@bp.route('/<int:provider_id>')
@login_required
def view_provider(provider_id):
    db = get_db()
    proveedor = db.execute(
        'SELECT * FROM proveedores WHERE id = ?',
        (provider_id,)
    ).fetchone()

    if proveedor is None:
        flash('Proveedor no encontrado.', 'error')
        return redirect(url_for('providers.list_providers'))

    return render_template('proveedores/view.html', proveedor=proveedor)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_provider():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('providers.list_providers'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        tipo_proveedor = request.form['tipo_proveedor']
        error = None

        if not nombre:
            error = 'Name is required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO providers (nombre, telefono, email, tipo_proveedor) VALUES (?, ?, ?, ?)",
                    (nombre, telefono, email, tipo_proveedor),
                )
                db.commit()
                flash('Provider added successfully.', 'success')
                return redirect(url_for('providers.list_providers'))
            except db.IntegrityError:
                error = f"Provider {nombre} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    return render_template('proveedores/add.html')

@bp.route('/<int:provider_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_provider(provider_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('providers.list_providers'))

    provider = db.execute(
        'SELECT id, nombre, telefono, email, tipo_proveedor FROM providers WHERE id = ?',
        (provider_id,)
    ).fetchone()

    if provider is None:
        flash('Provider not found.', 'error')
        return redirect(url_for('providers.list_providers'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        tipo_proveedor = request.form['tipo_proveedor']
        error = None

        if not nombre:
            error = 'Name is required.'

        if error is None:
            try:
                db.execute(
                    "UPDATE providers SET nombre = ?, telefono = ?, email = ?, tipo_proveedor = ? WHERE id = ?",
                    (nombre, telefono, email, tipo_proveedor, provider_id),
                )
                db.commit()
                flash('Provider updated successfully.', 'success')
                return redirect(url_for('providers.list_providers'))
            except db.IntegrityError:
                error = f"Provider {nombre} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    return render_template('proveedores/edit.html', provider=provider)

@bp.route('/<int:provider_id>/delete', methods=('POST',))
@login_required
def delete_provider(provider_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('providers.list_providers'))

    try:
        db.execute('DELETE FROM providers WHERE id = ?', (provider_id,))
        db.commit()
        flash('Provider deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting provider: {e}', 'error')
        db.rollback()

    return redirect(url_for('providers.list_providers'))