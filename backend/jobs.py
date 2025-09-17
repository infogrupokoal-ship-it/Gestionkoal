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
    clients = db.execute('SELECT id, nombre FROM clientes').fetchall()
    assigned_users = db.execute('SELECT id, username FROM users WHERE role IN (\'admin\', \'jefe_obra\', \'tecnico\', \'autonomo\')').fetchall()

    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        direccion_id = request.form['direccion_id']
        equipo_id = request.form['equipo_id']
        source = request.form['source']
        tipo = request.form['tipo']
        prioridad = request.form['prioridad']
        estado = request.form['estado']
        sla_due = request.form['sla_due']
        asignado_a = request.form['asignado_a']
        descripcion = request.form['descripcion']
        creado_por = g.user['id'] # Assuming g.user is set by login_required

        error = None

        if not cliente_id:
            error = 'Client is required.'
        if not tipo:
            error = 'Type is required.'
        if not prioridad:
            error = 'Priority is required.'
        if not estado:
            error = 'Status is required.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'INSERT INTO tickets (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, creado_por, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, creado_por, descripcion)
                )
                db.commit()
                flash('Job added successfully!')
                return redirect(url_for('jobs.list_jobs')) # Assuming a list_jobs route exists
            except sqlite3.IntegrityError:
                error = f"An error occurred while adding the job."
            except Exception as e:
                error = f"An unexpected error occurred: {e}"
            
            if error:
                flash(error)

    # Fetch addresses and equipment dynamically based on selected client/address if needed,
    # for now, just pass empty lists or fetch all if not too many.
    addresses = [] # This will need to be fetched via AJAX or similar based on client_id selection
    equipment = [] # This will need to be fetched via AJAX or similar based on address_id selection

    return render_template('trabajos/form.html', clients=clients, addresses=addresses, equipment=equipment, assigned_users=assigned_users)

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
    job = db.execute('SELECT * FROM tickets WHERE id = ?', (job_id,)).fetchone()

    if job is None:
        flash('Job not found.')
        return redirect(url_for('jobs.list_jobs'))

    clients = db.execute('SELECT id, nombre FROM clientes').fetchall()
    assigned_users = db.execute('SELECT id, username FROM users WHERE role IN (\'admin\', \'jefe_obra\', \'tecnico\', \'autonomo\')').fetchall()

    if request.method == 'POST':
        cliente_id = request.form['cliente_id']
        direccion_id = request.form['direccion_id']
        equipo_id = request.form['equipo_id']
        source = request.form['source']
        tipo = request.form['tipo']
        prioridad = request.form['prioridad']
        estado = request.form['estado']
        sla_due = request.form['sla_due']
        asignado_a = request.form['asignado_a']
        descripcion = request.form['descripcion']

        error = None

        if not cliente_id:
            error = 'Client is required.'
        if not tipo:
            error = 'Type is required.'
        if not prioridad:
            error = 'Priority is required.'
        if not estado:
            error = 'Status is required.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'UPDATE tickets SET cliente_id = ?, direccion_id = ?, equipo_id = ?, source = ?, tipo = ?, prioridad = ?, estado = ?, sla_due = ?, asignado_a = ?, descripcion = ? WHERE id = ?',
                    (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, descripcion, job_id)
                )
                db.commit()
                flash('Job updated successfully!')
                return redirect(url_for('jobs.list_jobs'))
            except sqlite3.IntegrityError:
                error = f"An error occurred while updating the job."
            except Exception as e:
                error = f"An unexpected error occurred: {e}"
            
            if error:
                flash(error)

    addresses = [] # Placeholder
    equipment = [] # Placeholder

    return render_template('trabajos/form.html', job=job, clients=clients, addresses=addresses, equipment=equipment, assigned_users=assigned_users)

