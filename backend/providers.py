import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('providers', __name__, url_prefix='/proveedores')

@bp.route('/')
@login_required
def list_providers():
    db = get_db()
    providers = db.execute(
        'SELECT id, nombre, telefono, email FROM proveedores ORDER BY nombre'
    ).fetchall()
    return render_template('proveedores/list.html', providers=providers)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_provider():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        db = get_db()
        error = None

        if not nombre:
            error = 'Name is required.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'INSERT INTO proveedores (nombre, telefono, email) VALUES (?, ?, ?)',
                    (nombre, telefono, email)
                )
                db.commit()
                flash('Provider added successfully!')
                return redirect(url_for('providers.list_providers'))
            except sqlite3.IntegrityError:
                error = f"Provider {nombre} already exists."
            except Exception as e:
                error = f"An unexpected error occurred: {e}"
            
            if error:
                flash(error)

    return render_template('proveedores/form.html')

@bp.route('/<int:provider_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_provider(provider_id):
    db = get_db()
    provider = db.execute('SELECT id, nombre, telefono, email FROM proveedores WHERE id = ?', (provider_id,)).fetchone()

    if provider is None:
        flash('Provider not found.')
        return redirect(url_for('providers.list_providers'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        error = None

        if not nombre:
            error = 'Name is required.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'UPDATE proveedores SET nombre = ?, telefono = ?, email = ? WHERE id = ?',
                    (nombre, telefono, email, provider_id)
                )
                db.commit()
                flash('Provider updated successfully!')
                return redirect(url_for('providers.list_providers'))
            except sqlite3.IntegrityError:
                error = f"Provider {nombre} already exists."
            except Exception as e:
                error = f"An unexpected error occurred: {e}"
            
            if error:
                flash(error)

    return render_template('proveedores/form.html', provider=provider)
