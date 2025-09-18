import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3 # Added for IntegrityError

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('clients', __name__, url_prefix='/clients')

@bp.route('/')
@login_required
def list_clients():
    db = get_db()
    clients = db.execute(
        'SELECT id, nombre, telefono, email, nif FROM clientes ORDER BY nombre'
    ).fetchall()
    return render_template('clients/list.html', clients=clients)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_client():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        nif = request.form['nif']
        db = get_db()
        error = None

        if not nombre:
            error = 'El nombre es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'INSERT INTO clientes (nombre, telefono, email, nif) VALUES (?, ?, ?, ?)',
                    (nombre, telefono, email, nif)
                )
                db.commit()
                flash('¡Cliente añadido correctamente!')
                return redirect(url_for('clients.list_clients'))
            except db.IntegrityError:
                error = f"El cliente {nombre} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('clients/form.html')

@bp.route('/<int:client_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_client(client_id):
    db = get_db()
    client = db.execute('SELECT id, nombre, telefono, email, nif FROM clientes WHERE id = ?', (client_id,)).fetchone()

    if client is None:
        flash('Cliente no encontrado.')
        return redirect(url_for('clients.list_clients'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        nif = request.form['nif']
        error = None

        if not nombre:
            error = 'El nombre es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'UPDATE clientes SET nombre = ?, telefono = ?, email = ?, nif = ? WHERE id = ?',
                    (nombre, telefono, email, nif, client_id)
                )
                db.commit()
                flash('¡Cliente actualizado correctamente!')
                return redirect(url_for('clients.list_clients'))
            except db.IntegrityError:
                error = f"El cliente {nombre} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('clients/form.html', client=client)
