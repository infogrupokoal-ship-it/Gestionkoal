
from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('clients', __name__, url_prefix='/clients')

@bp.route('/')
@login_required
def list_clients():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    clients = db.execute('SELECT id, nombre, telefono, email, nif, is_ngo FROM clientes').fetchall()
    return render_template('clients/list.html', clients=clients)

@bp.route('/<int:client_id>')
@login_required
def view_client(client_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    client = db.execute(
        'SELECT * FROM clientes WHERE id = ?',
        (client_id,)
    ).fetchone()

    if client is None:
        flash('Cliente no encontrado.', 'error')
        return redirect(url_for('clients.list_clients'))

    return render_template('clients/view.html', client=client)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_client():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('clients.list_clients'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        nif = request.form['nif']
        is_ngo = 'is_ngo' in request.form
        error = None

        if not nombre:
            error = 'Name is required.'

        if error is None:
            try:
                db.execute(
                    "INSERT INTO clientes (nombre, telefono, email, nif, is_ngo) VALUES (?, ?, ?, ?, ?)",
                    (nombre, telefono, email, nif, is_ngo),
                )
                db.commit()
                flash('Client added successfully.', 'success')
                return redirect(url_for('clients.list_clients'))
            except db.IntegrityError:
                error = f"Client {nombre} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    return render_template('clients/add.html')

@bp.route('/<int:client_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_client(client_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('clients.list_clients'))

    client = db.execute(
        'SELECT id, nombre, telefono, email, nif, is_ngo FROM clientes WHERE id = ?',
        (client_id,)
    ).fetchone()

    if client is None:
        flash('Client not found.', 'error')
        return redirect(url_for('clients.list_clients'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        nif = request.form['nif']
        is_ngo = 'is_ngo' in request.form
        error = None

        if not nombre:
            error = 'Name is required.'

        if error is None:
            try:
                db.execute(
                    "UPDATE clientes SET nombre = ?, telefono = ?, email = ?, nif = ?, is_ngo = ? WHERE id = ?",
                    (nombre, telefono, email, nif, is_ngo, client_id),
                )
                db.commit()
                flash('Client updated successfully.', 'success')
                return redirect(url_for('clients.view_client', client_id=client_id))
            except db.IntegrityError:
                error = f"Client {nombre} already exists."
                db.rollback()
            except Exception as e:
                error = f"An error occurred: {e}"
                db.rollback()

        flash(error)

    return render_template('clients/edit.html', client=client)
