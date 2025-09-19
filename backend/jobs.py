import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3 # Added for IntegrityError

from backend.db import get_db
from backend.auth import login_required # Added for login_required decorator

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_job():
    db = get_db()
    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    autonomos = db.execute('SELECT id, username FROM users WHERE role = \'autonomo\' ORDER BY username').fetchall()

    if request.method == 'POST':
        # Extract all form data
        cliente_id = request.form.get('client_id')
        autonomo_id = request.form.get('autonomo_id')
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado')
        estado_pago = request.form.get('estado_pago')
        metodo_pago = request.form.get('metodo_pago')
        presupuesto = request.form.get('presupuesto')
        vat_rate = request.form.get('vat_rate')
        fecha_visita = request.form.get('fecha_visita')
        job_difficulty_rating = request.form.get('job_difficulty_rating')
        creado_por = g.user.id

        error = None
        if not cliente_id or not titulo:
            error = 'Cliente y Título son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                # Note: The table schema uses 'asignado_a' for the freelancer/technician
                db.execute(
                    '''INSERT INTO tickets (cliente_id, asignado_a, tipo, descripcion, estado, metodo_pago, estado_pago, creado_por)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (cliente_id, autonomo_id, titulo, descripcion, estado, metodo_pago, estado_pago, creado_por)
                )
                db.commit()
                flash('¡Trabajo añadido correctamente!')
                return redirect(url_for('jobs.list_jobs'))
            except sqlite3.Error as e:
                error = f"Ocurrió un error al añadir el trabajo: {e}"
                flash(error)

    # Default values for the form
    trabajo = {}
    return render_template('trabajos/form.html', 
                           title="Añadir Trabajo", 
                           trabajo=trabajo, 
                           clients=clients, 
                           autonomos=autonomos, 
                           candidate_autonomos=None)

@bp.route('/')
@login_required
def list_jobs():
    db = get_db()
    jobs = db.execute(
        '''
        SELECT
            t.id, t.tipo, t.prioridad, t.estado, t.descripcion,
            c.nombre AS client_nombre, u.username AS assigned_user_username
        FROM tickets t
        JOIN clientes c ON t.cliente_id = c.id
        LEFT JOIN users u ON t.asignado_a = u.id
        ORDER BY t.id DESC
        '''
    ).fetchall()
    return render_template('trabajos/list.html', jobs=jobs)

@bp.route('/<int:job_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_job(job_id):
    db = get_db()
    # Fetch the job/ticket first to ensure it exists
    trabajo = db.execute('SELECT * FROM tickets WHERE id = ?', (job_id,)).fetchone()

    if trabajo is None:
        flash('Trabajo no encontrado.')
        return redirect(url_for('jobs.list_jobs'))

    if request.method == 'POST':
        # Extract all form data
        cliente_id = request.form.get('client_id')
        autonomo_id = request.form.get('autonomo_id')
        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado')
        estado_pago = request.form.get('estado_pago')
        metodo_pago = request.form.get('metodo_pago')
        # ... get other fields as needed ...

        error = None
        if not cliente_id or not titulo:
            error = 'Cliente y Título son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE tickets SET 
                       cliente_id = ?, asignado_a = ?, tipo = ?, descripcion = ?, estado = ?, 
                       metodo_pago = ?, estado_pago = ?
                       WHERE id = ?''',
                    (cliente_id, autonomo_id, titulo, descripcion, estado, metodo_pago, estado_pago, job_id)
                )
                db.commit()
                flash('¡Trabajo actualizado correctamente!')
                return redirect(url_for('jobs.list_jobs'))
            except sqlite3.Error as e:
                error = f"Ocurrió un error al actualizar el trabajo: {e}"
                flash(error)
    
    # Pass existing data to the template
    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    autonomos = db.execute('SELECT id, username FROM users WHERE role = \'autonomo\' ORDER BY username').fetchall()
    
    return render_template('trabajos/form.html', 
                           title="Editar Trabajo", 
                           trabajo=trabajo, 
                           clients=clients, 
                           autonomos=autonomos, 
                           candidate_autonomos=None)

