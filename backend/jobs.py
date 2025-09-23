import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, current_app
)
import sqlite3 # Added for IntegrityError
import os
from werkzeug.utils import secure_filename

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
        if autonomo_id == '':
            autonomo_id = None

        titulo = request.form.get('titulo')
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado')
        estado_pago = request.form.get('estado_pago')
        metodo_pago = request.form.get('metodo_pago')
        presupuesto = request.form.get('presupuesto')
        vat_rate = request.form.get('vat_rate')
        fecha_visita = request.form.get('fecha_visita')
        job_difficulty_rating = request.form.get('job_difficulty_rating')
        creado_por = g.user.id if g.user.is_authenticated else 1

        error = None
        if not cliente_id or not titulo:
            error = 'Cliente y Título son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                # Note: The table schema uses 'asignado_a' for the freelancer/technician
                db.execute(
                    '''INSERT INTO tickets (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, creado_por, descripcion, metodo_pago, estado_pago)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (cliente_id, None, None, None, titulo, None, estado, None, autonomo_id, creado_por, descripcion, metodo_pago, estado_pago)
                )
                db.commit()
                flash('¡Trabajo añadido correctamente!')

                # --- Notification Logic ---
                from .notifications import add_notification, send_whatsapp_notification
                # Get client name for notification message
                client_name_row = db.execute('SELECT nombre FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
                client_name = client_name_row['nombre'] if client_name_row else 'Cliente desconocido'

                # Get admin user IDs
                admin_users = db.execute('SELECT u.id FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.code = ?', ('admin',)).fetchall()

                # Prepare notification message
                notification_message = (
                    f"Nuevo trabajo añadido por {g.user.username}: {titulo} para {client_name}."
                )

                # Notify creator
                add_notification(db, g.user.id, notification_message)
                send_whatsapp_notification(db, g.user.id, notification_message)

                # Notify admins
                for admin in admin_users:
                    if admin['id'] != g.user.id: # Avoid double notification for creator if they are admin
                        add_notification(db, admin['id'], notification_message)
                        send_whatsapp_notification(db, admin['id'], notification_message)

                # Notify assigned freelancer
                if autonomo_id:
                    freelancer_user = db.execute('SELECT id FROM users WHERE id = ?', (autonomo_id,)).fetchone()
                    if freelancer_user:
                        freelancer_notification_message = f"Se te ha asignado un nuevo trabajo: {titulo} para {client_name}."
                        add_notification(db, freelancer_user['id'], freelancer_notification_message)
                        send_whatsapp_notification(db, freelancer_user['id'], freelancer_notification_message)
                # --- End Notification Logic ---
                return redirect(url_for('jobs.list_jobs')) # Assuming a list_jobs route exists
            except sqlite3.Error as e:
                db.rollback()
                error = f"Ocurrió un error al añadir el trabajo: {e}"
                flash(error)
            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error inesperado: {e}"
                flash(error)
            
            # If an error occurred and was caught, but 'error' was not set (e.g., if flash was called directly)
            # or if the function somehow continued without setting 'error' after an exception
            if error is not None: # This check is redundant if error is always set in except blocks
                db.rollback() # Ensure rollback if error was set and not handled by specific except
                flash(error)
            
            # If an error occurred and was caught, but 'error' was not set (e.g., if flash was called directly)
            # or if the function somehow continued without setting 'error' after an exception
            if error is not None: # This check is redundant if error is always set in except blocks
                db.rollback() # Ensure rollback if error was set and not handled by specific except
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

        recibo_url = trabajo['recibo_url'] if trabajo else None # Keep existing URL if no new file is uploaded

        if 'receipt_photo' in request.files:
            receipt_photo = request.files['receipt_photo']
            if receipt_photo.filename != '':
                # Validate file type (e.g., images)
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
                if '.' in receipt_photo.filename and \
                   receipt_photo.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(receipt_photo.filename)
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True) # Ensure upload folder exists
                    file_path = os.path.join(upload_folder, filename)
                    receipt_photo.save(file_path)
                    recibo_url = url_for('uploaded_file', filename=filename) # Store URL path
                else:
                    error = 'Tipo de archivo no permitido para el recibo.'

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
                       metodo_pago = ?, estado_pago = ?, recibo_url = ?
                       WHERE id = ?''',
                    (cliente_id, autonomo_id, titulo, descripcion, estado, metodo_pago, estado_pago, recibo_url, job_id)
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

    # Fetch associated quotes
    presupuestos_asociados = db.execute(
        'SELECT id, estado, total FROM presupuestos WHERE ticket_id = ?',
        (job_id,)
    ).fetchall()

    # For each quote, fetch its items
    quotes_with_items = []
    for presupuesto in presupuestos_asociados:
        items = db.execute(
            'SELECT descripcion, qty, precio_unit FROM presupuesto_items WHERE presupuesto_id = ?',
            (presupuesto['id'],)
        ).fetchall()
        # Convert Row objects to dicts for easier template access
        quote_dict = dict(presupuesto)
        quote_dict['items'] = [dict(item) for item in items]
        quotes_with_items.append(quote_dict)
    
    return render_template('trabajos/form.html', 
                           title="Editar Trabajo", 
                           trabajo=trabajo, 
                           clients=clients, 
                           autonomos=autonomos, 
                           candidate_autonomos=None,
                           presupuestos_asociados=quotes_with_items)

