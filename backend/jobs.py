import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, current_app
)
import sqlite3 # Added for IntegrityError
import os
from werkzeug.utils import secure_filename
import secrets
from datetime import datetime, timedelta

from backend.db import get_db
from backend.auth import login_required # Added for login_required decorator
from backend.forms import get_client_choices, get_freelancer_choices, get_technician_choices # New imports
from backend.whatsapp_meta import save_whatsapp_log # Import save_whatsapp_log
from backend.wa_client import send_whatsapp_message # Import send_whatsapp_message
from backend.market_study import get_market_study_for_material # Import the helper

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_job():
    try:
        db = get_db()
        clients = get_client_choices() # Refactored
        autonomos = get_freelancer_choices() # Refactored

        if request.method == 'POST':
            # Extract all form data
            cliente_id = request.form.get('client_id')
            autonomo_id = request.form.get('autonomo_id')
            if autonomo_id == '':
                autonomo_id = None

            tipo = request.form.get('tipo')
            titulo = request.form.get('titulo')
            descripcion = request.form.get('descripcion')
            estado = request.form.get('estado')
            estado_pago = request.form.get('estado_pago')
            metodo_pago = request.form.get('metodo_pao')
            presupuesto = request.form.get('presupuesto')
            vat_rate = request.form.get('vat_rate')
            fecha_visita = request.form.get('fecha_visita')
            job_difficulty_rating = request.form.get('job_difficulty_rating')
            creado_por = g.user.id if g.user.is_authenticated else 1

            error = None
            if not cliente_id or not titulo or not tipo:
                error = 'Cliente, Tipo y Título son obligatorios.'

            if error is not None:
                flash(error)
            else:
                try:
                    # Note: The table schema uses 'asignado_a' for the freelancer/technician
                    db.execute(
                        '''INSERT INTO tickets (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, creado_por, titulo, descripcion, metodo_pago, estado_pago, presupuesto, vat_rate, fecha_visita, job_difficulty_rating)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (cliente_id, None, None, None, tipo, None, estado, None, autonomo_id, creado_por, titulo, descripcion, metodo_pago, estado_pago, presupuesto, vat_rate, fecha_visita, job_difficulty_rating)
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

        # Default values for the form
        trabajo = {}
        return render_template('trabajos/form.html', 
                               title="Añadir Trabajo", 
                               trabajo=trabajo, 
                               clients=clients, 
                               autonomos=autonomos, 
                               candidate_autonomos=None)
    except Exception as e:
        current_app.logger.error(f"Error in add_job: {e}", exc_info=True)
        return "An internal server error occurred.", 500
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

@bp.route('/<int:job_id>')
@login_required
def view_job(job_id):
    db = get_db()
    job = db.execute(
        '''
        SELECT
            t.id, t.descripcion, t.estado, t.fecha_creacion, t.fecha_inicio, t.fecha_fin,
            t.cliente_id, c.nombre AS client_name, c.telefono AS client_phone, c.email AS client_email,
            t.asignado_a, u.username AS assigned_user_name, u.email AS assigned_user_email,
            t.prioridad, t.tipo_trabajo, t.ubicacion, t.observaciones, t.presupuesto_aprobado,
            t.costo_estimado, t.costo_real, t.margen_beneficio, t.fecha_cierre,
            t.metodo_pago, t.estado_pago, t.fecha_pago, t.provision_fondos, t.fecha_transferencia
        FROM tickets t
        LEFT JOIN clientes c ON t.cliente_id = c.id
        LEFT JOIN users u ON t.asignado_a = u.id
        WHERE t.id = ?
        ''',
        (job_id,)
    ).fetchone()

    if job is None:
        flash('Trabajo no encontrado.', 'error')
        return redirect(url_for('jobs.list_jobs'))

    # Fetch associated services for this job
    services = db.execute(
        '''
        SELECT
            js.service_id, s.name, s.description, js.quantity, js.price_per_unit, js.total_price
        FROM job_services js
        JOIN services s ON js.service_id = s.id
        WHERE js.job_id = ?
        ''',
        (job_id,)
    ).fetchall()

    # Fetch associated materials for this job
    materials = db.execute(
        '''
        SELECT
            jm.material_id, m.nombre, m.sku, jm.quantity, jm.price_per_unit, jm.total_price
        FROM job_materials jm
        JOIN materiales m ON jm.material_id = m.id
        WHERE jm.job_id = ?
        ''',
        (job_id,)
    ).fetchall()

    # Fetch all providers for the quote request dropdown
    providers = db.execute(
        'SELECT id, nombre FROM providers ORDER BY nombre'
    ).fetchall()

    # Fetch existing provider quotes for this job
    existing_quotes = db.execute(
        '''
        SELECT
            pq.material_id, pq.provider_id, p.nombre as provider_name, pq.quote_amount, pq.status, pq.quote_date,
            pq.payment_status, pq.payment_date -- New fields
        FROM provider_quotes pq
        JOIN providers p ON pq.provider_id = p.id
        WHERE pq.job_id = ?
        ORDER BY pq.quote_date DESC
        ''',
        (job_id,)
    ).fetchall()

    # Organize existing quotes by material_id for easier access in template
    quotes_by_material = {}
    for quote in existing_quotes:
        if quote['material_id'] not in quotes_by_material:
            quotes_by_material[quote['material_id']] = []
        quotes_by_material[quote['material_id']].append(quote)

    # Fetch market study data for each material
    materials_with_market_study = []
    for material in materials:
        material_dict = dict(material)
        market_study_data = get_market_study_for_material(material['material_id'])
        material_dict['market_study'] = market_study_data
        materials_with_market_study.append(material_dict)

    return render_template('jobs/view.html', job=job, services=services, materials=materials_with_market_study, providers=providers, quotes_by_material=quotes_by_material)

@bp.route('/<int:job_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_job(job_id):
    try:
        db = get_db()
        # Fetch the job/ticket first to ensure it exists
        trabajo = db.execute('SELECT * FROM tickets WHERE id = ?', (job_id,)).fetchone()
        if trabajo is None:
            flash('Trabajo no encontrado.')
            return redirect(url_for('jobs.list_jobs'))

        current_app.logger.info(f"Editing job: {dict(trabajo)}")

        original_estado = trabajo['estado']
        original_estado_pago = trabajo['estado_pago']

        if request.method == 'POST':
            # Extract all form data
            cliente_id = request.form.get('client_id')
            autonomo_id = request.form.get('autonomo_id')
            tipo = request.form.get('tipo')
            titulo = request.form.get('titulo')
            descripcion = request.form.get('descripcion')
            estado = request.form.get('estado')
            estado_pago = request.form.get('estado_pago')
            metodo_pago = request.form.get('metodo_pago')
            presupuesto = request.form.get('presupuesto')
            vat_rate = request.form.get('vat_rate')
            fecha_visita = request.form.get('fecha_visita')
            job_difficulty_rating = request.form.get('job_difficulty_rating')

            recibo_url = trabajo['recibo_url'] if trabajo else None # Keep existing URL if no new file is uploaded
            error = None # Initialize error before checks

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

            if not cliente_id or not titulo or not tipo:
                error = 'Cliente, Tipo y Título son obligatorios.'

            if error is not None:
                flash(error)
            else:
                db.execute(
                    '''UPDATE tickets SET 
                       cliente_id = ?, asignado_a = ?, tipo = ?, titulo = ?, descripcion = ?, estado = ?, 
                       metodo_pago = ?, estado_pago = ?, recibo_url = ?, presupuesto = ?, vat_rate = ?, fecha_visita = ?, job_difficulty_rating = ?
                       WHERE id = ?''',
                    (cliente_id, autonomo_id, tipo, titulo, descripcion, estado, metodo_pago, estado_pago, recibo_url, presupuesto, vat_rate, fecha_visita, job_difficulty_rating, job_id)
                )
                db.commit()
                flash('¡Trabajo actualizado correctamente!')

                # --- WhatsApp Notification for Status Changes ---
                from .notifications import send_whatsapp_notification
                
                # Fetch client and technician details for notifications
                client_data = db.execute(
                    'SELECT nombre, whatsapp_number, whatsapp_opt_in FROM clientes WHERE id = ?',
                    (cliente_id,)
                ).fetchone()
                technician_data = None
                if autonomo_id:
                    technician_data = db.execute(
                        'SELECT username, whatsapp_number, whatsapp_opt_in FROM users WHERE id = ?',
                        (autonomo_id,)
                    ).fetchone()

                # Notify on job status change
                if estado != original_estado:
                    status_change_message = f"El estado de su trabajo '{titulo}' ha cambiado de '{original_estado}' a '{estado}'."
                    if client_data and client_data['whatsapp_opt_in'] and client_data['whatsapp_number']:
                        send_whatsapp_notification(db, client_data['id'], status_change_message)
                    if technician_data and technician_data['whatsapp_opt_in'] and technician_data['whatsapp_number']:
                        send_whatsapp_notification(db, autonomo_id, status_change_message)

                # Notify on payment status change
                if estado_pago != original_estado_pago:
                    payment_status_change_message = f"El estado de pago de su trabajo '{titulo}' ha cambiado de '{original_estado_pago}' a '{estado_pago}'."
                    if client_data and client_data['whatsapp_opt_in'] and client_data['whatsapp_number']:
                        send_whatsapp_notification(db, client_data['id'], payment_status_change_message)
                    if technician_data and technician_data['whatsapp_opt_in'] and technician_data['whatsapp_number']:
                        send_whatsapp_notification(db, autonomo_id, payment_status_change_message)
                # --- End WhatsApp Notification for Status Changes ---

                # --- PDF Receipt Generation Logic ---
                if estado_pago == 'Pagado':
                    # Fetch full job details for PDF
                    full_job_details = db.execute(
                        '''SELECT t.*, c.nombre as client_name, c.telefono as client_phone, c.email as client_email, c.is_ngo,
                           u.username as technician_name, u.telefono as technician_phone,
                           p.total as quote_total
                           FROM tickets t
                           LEFT JOIN clientes c ON t.cliente_id = c.id
                           LEFT JOIN users u ON t.asignado_a = u.id
                           LEFT JOIN presupuestos p ON t.id = p.ticket_id
                           WHERE t.id = ?''',
                        (job_id,)
                    ).fetchone()

                    if full_job_details:
                        job_details_for_pdf = {
                            'id': full_job_details['id'],
                            'description': full_job_details['descripcion'],
                            'status': full_job_details['estado'],
                            'payment_method': full_job_details['metodo_pago'],
                            'payment_status': full_job_details['estado_pago'],
                            'amount': full_job_details['quote_total'] if full_job_details['quote_total'] is not None else 0.0
                        }
                        client_details_for_pdf = {
                            'name': full_job_details['client_name'],
                            'phone': full_job_details['client_phone'],
                            'email': full_job_details['client_email']
                        }
                        technician_details_for_pdf = {
                            'name': full_job_details['technician_name'],
                            'phone': full_job_details['technician_phone']
                        } if full_job_details['technician_name'] else None

                        company_details = {
                            'name': 'Grupo Koal',
                            'address': 'Tu Dirección, Tu Ciudad',
                            'phone': 'Tu Teléfono',
                            'email': 'tu@email.com'
                        }

                        # Generate unique filename
                        pdf_filename = f"recibo_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                        upload_folder = current_app.config['UPLOAD_FOLDER']
                        os.makedirs(upload_folder, exist_ok=True)
                        pdf_filepath = os.path.join(upload_folder, pdf_filename)

                        from backend.receipt_generator import generate_receipt_pdf
                        current_app.logger.info(f"Generating PDF with the following data: output_path={pdf_filepath}, job_details={job_details_for_pdf}, client_details={client_details_for_pdf}, company_details={company_details}, is_ngo={bool(full_job_details['is_ngo'])}, technician_details={technician_details_for_pdf}")
                        generate_receipt_pdf(
                            output_path=pdf_filepath, 
                            job_details=job_details_for_pdf, 
                            client_details=client_details_for_pdf, 
                            company_details=company_details, 
                            is_ngo=bool(full_job_details['is_ngo']), 
                            technician_details=technician_details_for_pdf
                        )

                        recibo_url = url_for('uploaded_file', filename=pdf_filename) # Store URL path
                        db.execute('UPDATE tickets SET recibo_url = ? WHERE id = ?', (recibo_url, job_id))
                        db.commit()
                        flash('¡Recibo PDF generado y guardado correctamente!', 'success')
                # --- End PDF Receipt Generation Logic ---

                # --- Payment Confirmation Link Logic ---
                if estado_pago in ['Pendiente', 'Facturado']:
                    token = secrets.token_urlsafe(32)
                    expires_at = datetime.now() + timedelta(days=7) # Link valid for 7 days
                    
                    db.execute(
                        'UPDATE tickets SET payment_confirmation_token = ?, payment_confirmation_expires = ? WHERE id = ?',
                        (token, expires_at.strftime('%Y-%m-%d %H:%M:%S'), job_id)
                    )
                    db.commit()

                    # Fetch client's WhatsApp number
                    client_data = db.execute(
                        'SELECT whatsapp_number, whatsapp_opt_in FROM users WHERE id = ?',
                        (cliente_id,)
                    ).fetchone()

                    if client_data and client_data['whatsapp_opt_in'] and client_data['whatsapp_number']:
                        confirmation_url = url_for('payment_confirmation.confirm_payment', ticket_id=job_id, token=token, _external=True)
                        whatsapp_message = f"Hola! Por favor, confirma el pago de tu trabajo ({titulo}) aquí: {confirmation_url}"
                        from .notifications import send_whatsapp_notification
                        send_whatsapp_notification(db, cliente_id, whatsapp_message)
                        flash('Enlace de confirmación de pago enviado al cliente por WhatsApp.', 'info')
                # --- End Payment Confirmation Link Logic ---

                return redirect(url_for('jobs.list_jobs'))

        # Pass existing data to the template
        clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
        autonomos = db.execute("SELECT id, username FROM users WHERE role = 'autonomo' ORDER BY username").fetchall()

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
        
        # Fetch associated expenses
        gastos = db.execute(
            'SELECT g.*, u.username as pagado_por_username FROM gastos_compartidos g JOIN users u ON g.pagado_por = u.id WHERE g.ticket_id = ? ORDER BY g.fecha DESC',
            (job_id,)
        ).fetchall()

        # Fetch associated tasks
        tareas = db.execute(
            'SELECT tt.*, u.username as asignado_a_username FROM ticket_tareas tt LEFT JOIN users u ON tt.asignado_a = u.id WHERE tt.ticket_id = ? ORDER BY tt.created_at DESC',
            (job_id,)
        ).fetchall()

        return render_template('trabajos/form.html', 
                               title="Editar Trabajo", 
                               trabajo=trabajo, 
                               clients=clients, 
                               autonomos=autonomos, 
                               candidate_autonomos=None,
                               presupuestos_asociados=quotes_with_items,
                               gastos=gastos,
                               tareas=tareas)
    except Exception as e:
        current_app.logger.error(f"Error in edit_job: {e}", exc_info=True)
        return "An internal server error occurred.", 500

@bp.route('/<int:job_id>/materials/<int:material_id>/request_quote', methods=['POST'])
@login_required
def request_material_quote(job_id, material_id):
    db = get_db()
    provider_id = request.form.get('provider_id')

    if not provider_id:
        flash('Debe seleccionar un proveedor para solicitar la cotización.', 'error')
        return redirect(url_for('jobs.view_job', job_id=job_id))

    try:
        # Fetch material details
        material = db.execute('SELECT nombre, descripcion FROM materiales WHERE id = ?', (material_id,)).fetchone()
        if not material:
            flash('Material no encontrado.', 'error')
            return redirect(url_for('jobs.view_job', job_id=job_id))

        # Fetch provider details
        provider = db.execute('SELECT nombre, whatsapp_number FROM providers WHERE id = ?', (provider_id,)).fetchone()
        if not provider or not provider['whatsapp_number']:
            flash('Proveedor no encontrado o sin número de WhatsApp.', 'error')
            return redirect(url_for('jobs.view_job', job_id=job_id))

        # Construct message
        message_body = (
            f"Hola {provider['nombre']},\n"
            f"Necesitamos una cotización para el material: {material['nombre']} (ID: {material_id}).\n"
            f"Descripción: {material['descripcion']}.\n"
            f"Para el trabajo ID: {job_id}.\n"
            f"Por favor, envíanos tu mejor precio y disponibilidad."
        )

        # Send WhatsApp message
        to_number = provider['whatsapp_number']
        message_id = send_whatsapp_message(to_number, message_body)

        if message_id:
            # Insert into provider_quotes table
            db.execute(
                """
                INSERT INTO provider_quotes (job_id, material_id, provider_id, status, whatsapp_message_id, payment_status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, material_id, provider_id, 'pending', message_id, 'pending') # Added payment_status
            )
            db.commit()
            # Log the outbound message
            save_whatsapp_log(
                job_id=job_id,
                material_id=material_id,
                provider_id=provider_id,
                direction='outbound',
                from_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
                to_number=to_number,
                message_body=message_body,
                whatsapp_message_id=message_id,
                status='sent'
            )
            flash('Solicitud de cotización enviada por WhatsApp.', 'success')
        else:
            flash('Error al enviar la solicitud de cotización por WhatsApp.', 'error')
            # Log failure
            save_whatsapp_log(
                job_id=job_id,
                material_id=material_id,
                provider_id=provider_id,
                direction='outbound',
                from_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
                to_number=to_number,
                message_body=message_body,
                whatsapp_message_id=None,
                status='failed',
                error_info='Failed to get message ID from WhatsApp API'
            )

    except Exception as e:
        current_app.logger.error(f"Error requesting material quote: {e}", exc_info=True)
        flash(f'Ocurrió un error al solicitar la cotización: {e}', 'error')

    return redirect(url_for('jobs.view_job', job_id=job_id))

@bp.route('/<int:trabajo_id>/gastos/add', methods=('GET', 'POST'))
@login_required
def add_gasto(trabajo_id):
    db = get_db()
    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        monto = request.form.get('monto')
        fecha = request.form.get('fecha') or datetime.now().strftime('%Y-%m-%d')
        pagado_por = request.form.get('pagado_por') or g.user.id
        
        if not descripcion or not monto:
            flash('Descripción y monto son obligatorios.', 'error')
        else:
            try:
                db.execute(
                    'INSERT INTO gastos_compartidos (ticket_id, descripcion, monto, fecha, creado_por, pagado_por) VALUES (?, ?, ?, ?, ?, ?)',
                    (trabajo_id, descripcion, monto, fecha, g.user.id, pagado_por)
                )
                db.commit()
                flash('Gasto añadido correctamente.')
                return redirect(url_for('jobs.edit_job', job_id=trabajo_id))
            except db.Error as e:
                db.rollback()
                flash(f'Error al añadir el gasto: {e}', 'error')

    users = db.execute('SELECT id, username FROM users').fetchall()
    return render_template('gastos/form.html', title="Añadir Gasto", trabajo_id=trabajo_id, users=users)

@bp.route('/gastos/<int:gasto_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_gasto(gasto_id):
    db = get_db()
    gasto = db.execute('SELECT * FROM gastos_compartidos WHERE id = ?', (gasto_id,)).fetchone()
    if gasto is None:
        flash('Gasto no encontrado.', 'error')
        return redirect(url_for('jobs.list_jobs'))

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        monto = request.form.get('monto')
        fecha = request.form.get('fecha')
        pagado_por = request.form.get('pagado_por')

        if not descripcion or not monto:
            flash('Descripción y monto son obligatorios.', 'error')
        else:
            try:
                db.execute(
                    'UPDATE gastos_compartidos SET descripcion = ?, monto = ?, fecha = ?, pagado_por = ? WHERE id = ?',
                    (descripcion, monto, fecha, pagado_por, gasto_id)
                )
                db.commit()
                flash('Gasto actualizado correctamente.')
                return redirect(url_for('jobs.edit_job', job_id=gasto['ticket_id']))
            except db.Error as e:
                db.rollback()
                flash(f'Error al actualizar el gasto: {e}', 'error')
    
    users = db.execute('SELECT id, username FROM users').fetchall()
    return render_template('gastos/form.html', title="Editar Gasto", gasto=gasto, trabajo_id=gasto['ticket_id'], users=users)

@bp.route('/gastos/<int:gasto_id>/delete', methods=('POST',))
@login_required
def delete_gasto(gasto_id):
    db = get_db()
    gasto = db.execute('SELECT ticket_id FROM gastos_compartidos WHERE id = ?', (gasto_id,)).fetchone()
    if gasto:
        try:
            db.execute('DELETE FROM gastos_compartidos WHERE id = ?', (gasto_id,))
            db.commit()
            flash('Gasto eliminado correctamente.')
        except db.Error as e:
            db.rollback()
            flash(f'Error al eliminar el gasto: {e}', 'error')
        return redirect(url_for('jobs.edit_job', job_id=gasto['ticket_id']))
    else:
        flash('Gasto no encontrado.', 'error')
        return redirect(url_for('jobs.list_jobs'))

@bp.route('/<int:trabajo_id>/tareas/add', methods=('GET', 'POST'))
@login_required
def add_tarea(trabajo_id):
    db = get_db()
    suggested_surcharge = None # Initialize

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        asignado_a = request.form.get('asignado_a') or None
        metodo_pago = request.form.get('metodo_pago')
        estado_pago = request.form.get('estado_pago')
        error = None

        if not descripcion:
            flash('La descripción de la tarea es obligatoria.', 'error')
        else:
            try:
                db.execute(
                    'INSERT INTO ticket_tareas (ticket_id, descripcion, asignado_a, creado_por, metodo_pago, estado_pago) VALUES (?, ?, ?, ?, ?, ?)',
                    (trabajo_id, descripcion, asignado_a, g.user.id, metodo_pago, estado_pago)
                )
                db.commit()
                flash('Tarea añadida correctamente.')
                return redirect(url_for('jobs.edit_job', job_id=trabajo_id))
            except db.Error as e:
                db.rollback()
                flash(f'Error al añadir la tarea: {e}', 'error')

    # For GET request or if POST fails, fetch job_difficulty_rating
    users = db.execute("SELECT id, username, costo_por_hora, tasa_recargo FROM users WHERE role IN ('tecnico', 'autonomo', 'admin')").fetchall()
    job_difficulty_rating_row = db.execute('SELECT job_difficulty_rating FROM tickets WHERE id = ?', (trabajo_id,)).fetchone()
    job_difficulty_rating = job_difficulty_rating_row['job_difficulty_rating'] if job_difficulty_rating_row else 0

    return render_template('tareas/form.html', title="Añadir Tarea", trabajo_id=trabajo_id, users=users, job_difficulty_rating=job_difficulty_rating)

@bp.route('/tareas/<int:tarea_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_tarea(tarea_id):
    db = get_db()
    tarea = db.execute('SELECT * FROM ticket_tareas WHERE id = ?', (tarea_id,)).fetchone()
    if tarea is None:
        flash('Tarea no encontrada.', 'error')
        return redirect(url_for('jobs.list_jobs'))

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        estado = request.form.get('estado')
        asignado_a = request.form.get('asignado_a') or None
        metodo_pago = request.form.get('metodo_pago')
        estado_pago = request.form.get('estado_pago')
        error = None

        if not descripcion:
            flash('La descripción es obligatoria.', 'error')
        else:
            try:
                db.execute(
                    'UPDATE ticket_tareas SET descripcion = ?, estado = ?, asignado_a = ?, metodo_pago = ?, estado_pago = ? WHERE id = ?',
                    (descripcion, estado, asignado_a, metodo_pago, estado_pago, tarea_id)
                )
                db.commit()
                flash('Tarea actualizada correctamente.')
                return redirect(url_for('jobs.edit_job', job_id=tarea['ticket_id']))
            except db.Error as e:
                db.rollback()
                flash(f'Error al actualizar la tarea: {e}', 'error')
    
    # For GET request or if POST fails, fetch job_difficulty_rating and user details
    users = db.execute("SELECT id, username, costo_por_hora, tasa_recargo FROM users WHERE role IN ('tecnico', 'autonomo', 'admin')").fetchall()
    job_difficulty_rating_row = db.execute('SELECT job_difficulty_rating FROM tickets WHERE id = ?', (tarea['ticket_id'],)).fetchone()
    job_difficulty_rating = job_difficulty_rating_row['job_difficulty_rating'] if job_difficulty_rating_row else 0

    return render_template('tareas/form.html', title="Editar Tarea", tarea=tarea, trabajo_id=tarea['ticket_id'], users=users, job_difficulty_rating=job_difficulty_rating)

@bp.route('/tareas/<int:tarea_id>/delete', methods=('POST',))
@login_required
def delete_tarea(tarea_id):
    db = get_db()
    tarea = db.execute('SELECT ticket_id FROM ticket_tareas WHERE id = ?', (tarea_id,)).fetchone()
    if tarea:
        try:
            db.execute('DELETE FROM ticket_tareas WHERE id = ?', (tarea_id,))
            db.commit()
            flash('Tarea eliminada correctamente.')
        except db.Error as e:
            db.rollback()
            flash(f'Error al eliminar la tarea: {e}', 'error')
        return redirect(url_for('jobs.edit_job', job_id=tarea['ticket_id']))
    else:
        flash('Tarea no encontrada.', 'error')
        return redirect(url_for('jobs.list_jobs'))
