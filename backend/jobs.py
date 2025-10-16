import json
import os
import sqlite3  # Added for IntegrityError
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from backend.db import get_db
from backend.forms import get_client_choices, get_freelancer_choices  # New imports
from backend.market_study import get_market_study_for_material  # Import the helper
from backend.whatsapp import send_whatsapp_text  # Import send_whatsapp_text
from backend.whatsapp_meta import save_whatsapp_log  # Import save_whatsapp_log

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_job():
    try:
        db = get_db()
        if db is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('jobs.list_jobs'))
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
            metodo_pago = request.form.get('metodo_pago')
            presupuesto = request.form.get('presupuesto')
            vat_rate = request.form.get('vat_rate')
            fecha_visita = request.form.get('fecha_visita')
            job_difficulty_rating = request.form.get('job_difficulty_rating')
            creado_por = g.user.id if g.user.is_authenticated else 1

            if not cliente_id or not titulo or not tipo:
                error = 'Cliente, Tipo y Título son obligatorios.'

            # Backend validation for NGO cash payment rule
            if cliente_id:
                client_data = db.execute('SELECT is_ngo FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
                if client_data and bool(client_data['is_ngo']) and metodo_pago != 'Efectivo':
                    error = 'Las ONG sin ánimo de lucro deben pagar en efectivo.'

            if error is not None:
                flash(error)
            else:
                try:
                    # Note: The table schema uses 'asignado_a' for the freelancer/technician
                    result = db.execute(
                        '''INSERT INTO tickets (cliente_id, direccion_id, equipo_id, source, tipo, prioridad, estado, sla_due, asignado_a, creado_por, titulo, descripcion, metodo_pago, estado_pago, presupuesto, vat_rate, fecha_visita, job_difficulty_rating)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (cliente_id, None, None, None, tipo, None, estado, None, autonomo_id, creado_por, titulo, descripcion, metodo_pago, estado_pago, presupuesto, vat_rate, fecha_visita, job_difficulty_rating)
                    )
                    job_id = result.lastrowid # Get the last inserted row ID
                    db.commit()
                    flash('¡Trabajo añadido correctamente!')

                    # --- Notification Logic ---
                    from .notifications import (
                        add_notification,
                        send_whatsapp_notification,
                    )
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

                    # Record income in financial_transactions if created as Paid
                    if estado_pago == 'Pagado':
                        amount = float(presupuesto) if presupuesto else 0.0
                        vat_rate_val = float(vat_rate) if vat_rate else 0.0
                        vat_amount = amount * (vat_rate_val / 100)
                        total_amount = amount + vat_amount
                        db.execute(
                            '''INSERT INTO financial_transactions (ticket_id, type, amount, description, recorded_by, vat_rate, vat_amount)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (job_id, 'income', total_amount, f'Pago de trabajo {titulo}', g.user.id, vat_rate_val, vat_amount)
                        )
                        flash('Ingreso registrado en transacciones financieras.', 'info')

                    # Record expense for provision_fondos if set
                    new_provision_fondos = float(request.form.get('provision_fondos')) if request.form.get('provision_fondos') else 0.0
                    if new_provision_fondos > 0:
                        db.execute(
                            '''INSERT INTO financial_transactions (ticket_id, type, amount, description, recorded_by)
                               VALUES (?, ?, ?, ?, ?)''',
                            (job_id, 'expense', new_provision_fondos, f'Provisión de fondos para trabajo {titulo}', g.user.id)
                        )
                        flash('Provisión de fondos registrada como gasto.', 'info')

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
        client_is_ngo = False
        # Fetch all clients with their is_ngo status for JavaScript
        all_clients_data = db.execute('SELECT id, nombre, is_ngo FROM clientes').fetchall()
        clients_json = json.dumps([dict(c) for c in all_clients_data])

        if request.method == 'GET' and request.args.get('client_id'):
            client_id = request.args.get('client_id', type=int)
            client_data = db.execute('SELECT is_ngo FROM clientes WHERE id = ?', (client_id,)).fetchone()
            if client_data:
                client_is_ngo = bool(client_data['is_ngo'])

        return render_template('trabajos/form.html',
                               title="Añadir Trabajo",
                               trabajo=trabajo,
                               clients=clients,
                               autonomos=autonomos,
                               candidate_autonomos=None,
                               client_is_ngo=client_is_ngo,
                               all_clients_data=clients_json)
    except Exception as e:
        current_app.logger.error(f"Error in add_job: {e}", exc_info=True)
        return "An internal server error occurred.", 500
@bp.route('/')
@login_required
def list_jobs():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    jobs = db.execute(
        """
        SELECT t.id, t.descripcion, t.estado, t.prioridad, t.tipo, c.nombre as client_name, u.username as assigned_to_name, e.inicio, e.fin
        FROM tickets t
        LEFT JOIN clientes c ON t.cliente_id = c.id
        LEFT JOIN users u ON t.asignado_a = u.id
        LEFT JOIN eventos e ON t.id = e.ticket_id
        ORDER BY t.created_at DESC
        """
    ).fetchall()
    return render_template('trabajos/list.html', jobs=jobs)

@bp.route('/<int:job_id>')
@login_required
def view_job(job_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

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
            pq.id, pq.material_id, pq.provider_id, p.nombre as provider_name, pq.quote_amount, pq.status, pq.quote_date,
            pq.payment_status, pq.payment_date # New fields
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

    # Fetch freelancer quotes for this job
    freelancer_quotes = db.execute(
        '''
        SELECT
            p.id, p.total, p.estado, p.fecha_creacion, p.billing_entity_type, p.billing_entity_id,
            u.username AS freelancer_name
        FROM presupuestos p
        JOIN users u ON p.freelancer_id = u.id
        WHERE p.ticket_id = ? AND p.freelancer_id IS NOT NULL
        ORDER BY p.fecha_creacion DESC
        ''',
        (job_id,)
    ).fetchall()

    # For each freelancer quote, fetch its associated files
    freelancer_quotes_with_files = []
    for f_quote in freelancer_quotes:
        f_quote_dict = dict(f_quote)
        f_quote_dict['files'] = db.execute(
            'SELECT id, url, tipo FROM ficheros WHERE presupuesto_id = ?',
            (f_quote['id'],)
        ).fetchall()
        freelancer_quotes_with_files.append(f_quote_dict)

    return render_template('jobs/view.html', job=job, services=services, materials=materials_with_market_study, providers=providers, quotes_by_material=quotes_by_material, freelancer_quotes=freelancer_quotes_with_files)

@bp.route('/<int:job_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_job(job_id):
    db = get_db()
    # Fetch the job using a more comprehensive query that gets all necessary fields upfront
    job = db.execute(
        'SELECT * FROM tickets WHERE id = ?', (job_id,)
    ).fetchone()

    if job is None:
        flash('Trabajo no encontrado.', 'error')
        return redirect(url_for('jobs.list_jobs'))

    # Store original values to detect changes
    original_estado = job['estado']
    original_estado_pago = job['estado_pago']

    if request.method == 'POST':
        try:
            # --- 1. Read Form Data ---
            cliente_id = request.form.get('client_id', type=int)
            autonomo_id = request.form.get('autonomo_id', type=int)
            if autonomo_id == 0:
                autonomo_id = None  # Handle placeholder value
            tipo = request.form.get('tipo')
            titulo = request.form.get('titulo')
            descripcion = request.form.get('descripcion')
            estado = request.form.get('estado')
            estado_pago = request.form.get('estado_pago')
            metodo_pago = request.form.get('metodo_pago')
            presupuesto = request.form.get('presupuesto', type=float)
            vat_rate = request.form.get('vat_rate', type=float)
            fecha_visita = request.form.get('fecha_visita')
            job_difficulty_rating = request.form.get('job_difficulty_rating', type=int)

            recibo_url = job['recibo_url']  # Default to existing
            error = None

            # --- 2. Validate Form Data ---
            if not all([cliente_id, titulo, tipo]):
                error = 'Cliente, Tipo y Título son obligatorios.'

            if not error:
                client_data = db.execute('SELECT is_ngo FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
                if client_data and bool(client_data['is_ngo']) and metodo_pago != 'Efectivo':
                    error = 'Las ONG sin ánimo de lucro deben pagar en efectivo.'

            # --- 3. Handle File Upload ---
            if not error and 'receipt_photo' in request.files:
                receipt_photo = request.files['receipt_photo']
                if receipt_photo.filename != '':
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
                    if '.' in receipt_photo.filename and receipt_photo.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        filename = secure_filename(f"{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{receipt_photo.filename}")
                        upload_folder = current_app.config['UPLOAD_FOLDER']
                        os.makedirs(upload_folder, exist_ok=True)
                        file_path = os.path.join(upload_folder, filename)
                        receipt_photo.save(file_path)
                        recibo_url = url_for('static', filename=f'uploads/{filename}')
                    else:
                        error = 'Tipo de archivo no permitido para el recibo.'

            if error:
                flash(error, 'error')
            else:
                # --- 4. Update Database ---
                db.execute(
                    '''UPDATE tickets SET 
                       cliente_id = ?, asignado_a = ?, tipo = ?, titulo = ?, descripcion = ?, estado = ?, 
                       metodo_pago = ?, estado_pago = ?, recibo_url = ?, presupuesto = ?, vat_rate = ?, 
                       fecha_visita = ?, job_difficulty_rating = ?
                       WHERE id = ?''',
                    (cliente_id, autonomo_id, tipo, titulo, descripcion, estado, metodo_pago, estado_pago,
                     recibo_url, presupuesto, vat_rate, fecha_visita, job_difficulty_rating, job_id)
                )
                flash('¡Trabajo actualizado correctamente!', 'success')

                # --- 5. Notifications ---
                if estado != original_estado or estado_pago != original_estado_pago:
                    client_info = db.execute('SELECT whatsapp_number, whatsapp_opt_in FROM clientes WHERE id = ?', (cliente_id,)).fetchone()

                    if estado != original_estado:
                        msg = f"El estado de su trabajo '{titulo}' ha cambiado a '{estado}'."
                        if client_info and client_info['whatsapp_opt_in']:
                             send_whatsapp_text(client_info['whatsapp_number'], msg)

                    if estado_pago != original_estado_pago:
                        msg = f"El estado de pago de su trabajo '{titulo}' ha cambiado a '{estado_pago}'."
                        if client_info and client_info['whatsapp_opt_in']:
                            send_whatsapp_text(client_info['whatsapp_number'], msg)

                # --- 6. Financials & PDF Generation ---
                if estado_pago == 'Pagado' and original_estado_pago != 'Pagado':
                    # Record income transaction
                    amount = float(presupuesto) if presupuesto else 0.0
                    vat_amount = amount * (float(vat_rate) / 100 if vat_rate else 0.0)
                    total_amount = amount + vat_amount
                    db.execute(
                        '''INSERT INTO financial_transactions (ticket_id, type, amount, description, recorded_by, vat_rate, vat_amount)
                           VALUES (?, 'income', ?, ?, ?, ?, ?)''',
                        (job_id, total_amount, f'Pago de trabajo {titulo}', g.user.id, vat_rate, vat_amount)
                    )
                    flash('Ingreso registrado en transacciones financieras.', 'info')

                    # Generate PDF receipt
                    from backend.receipt_generator import generate_receipt_pdf
                    pdf_filename = f"recibo_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True)
                    pdf_filepath = os.path.join(upload_folder, pdf_filename)

                    # Fetch data needed for PDF
                    job_details_for_pdf = { 'id': job_id, 'description': descripcion, 'status': estado, 'payment_method': metodo_pago, 'payment_status': estado_pago, 'amount': total_amount }
                    client_details_for_pdf = db.execute('SELECT nombre as name, telefono as phone, email FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
                    company_details = {'name': 'Grupo Koal', 'address': 'Valencia, España', 'phone': 'N/A', 'email': 'info@grupokoal.com'}

                    generate_receipt_pdf(
                        output_path=pdf_filepath,
                        job_details=job_details_for_pdf,
                        client_details=dict(client_details_for_pdf),
                        company_details=company_details
                    )

                    # Update job with new PDF receipt URL
                    pdf_url = url_for('static', filename=f'uploads/{pdf_filename}')
                    db.execute('UPDATE tickets SET recibo_url = ? WHERE id = ?', (pdf_url, job_id))
                    flash('Recibo PDF generado y guardado.', 'success')

                db.commit()
                return redirect(url_for('jobs.list_jobs'))

        except sqlite3.Error as e:
            db.rollback()
            current_app.logger.error(f"Database error in edit_job: {e}")
            flash(f'Error de base de datos: {e}', 'error')
        except Exception as e:
            db.rollback()
            current_app.logger.error(f"Error in edit_job: {e}", exc_info=True)
            flash(f'Ocurrió un error inesperado: {e}', 'error')

    # --- GET Request Logic ---
    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    autonomos = db.execute("SELECT id, username FROM users WHERE 'autonomo' IN (SELECT r.code FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = users.id) ORDER BY username").fetchall()

    # Fetch related data for the form
    gastos = db.execute('SELECT * FROM gastos_compartidos WHERE ticket_id = ? ORDER BY fecha DESC', (job_id,)).fetchall()
    tareas = db.execute('SELECT * FROM ticket_tareas WHERE ticket_id = ? ORDER BY created_at DESC', (job_id,)).fetchall()

    return render_template('trabajos/form.html',
                               title="Editar Trabajo",
                               trabajo=job,
                               clients=clients,
                               autonomos=autonomos,
                               gastos=gastos,
                               tareas=tareas)

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
        message_id = send_whatsapp_text(to_number, message_body)

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
                error_info='Failed to get message ID from WhatsApp API',
                user_id=g.user.id # Added user_id
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

    if request.method == 'POST':
        descripcion = request.form.get('descripcion')
        asignado_a = request.form.get('asignado_a') or None
        metodo_pago = request.form.get('metodo_pago')
        estado_pago = request.form.get('estado_pago')
        provision_fondos = request.form.get('provision_fondos', type=float)
        fecha_transferencia = request.form.get('fecha_transferencia')

        if not descripcion:
            flash('La descripción de la tarea es obligatoria.', 'error')
        else:
            try:
                db.execute(
                    'INSERT INTO ticket_tareas (ticket_id, descripcion, asignado_a, creado_por, metodo_pago, estado_pago, provision_fondos, fecha_transferencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (trabajo_id, descripcion, asignado_a, g.user.id, metodo_pago, estado_pago, provision_fondos, fecha_transferencia)
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
        provision_fondos = request.form.get('provision_fondos', type=float)
        fecha_transferencia = request.form.get('fecha_transferencia')

        if not descripcion:
            flash('La descripción es obligatoria.', 'error')
        else:
            try:
                db.execute(
                    'UPDATE ticket_tareas SET descripcion = ?, estado = ?, asignado_a = ?, metodo_pago = ?, estado_pago = ?, provision_fondos = ?, fecha_transferencia = ? WHERE id = ?',
                    (descripcion, estado, asignado_a, metodo_pago, estado_pago, provision_fondos, fecha_transferencia, tarea_id)
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

@bp.route('/freelancer_quotes/<int:quote_id>/approve', methods=('POST',))
@login_required
def approve_freelancer_quote(quote_id):
    if not current_user.has_permission('approve_quotes'):
        flash('No tienes permiso para aprobar presupuestos.', 'error')
        return redirect(request.referrer or url_for('index'))

    db = get_db()
    quote = db.execute('SELECT ticket_id FROM presupuestos WHERE id = ?', (quote_id,)).fetchone()

    if quote is None:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(request.referrer or url_for('index'))

    try:
        db.execute('UPDATE presupuestos SET estado = ? WHERE id = ?', ('Aprobado', quote_id))
        db.commit()
        flash('Presupuesto aprobado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al aprobar el presupuesto: {e}', 'error')
        db.rollback()

    return redirect(url_for('jobs.view_job', job_id=quote['ticket_id']))

@bp.route('/freelancer_quotes/<int:quote_id>/reject', methods=('POST',))
@login_required
def reject_freelancer_quote(quote_id):
    if not current_user.has_permission('approve_quotes'):
        flash('No tienes permiso para rechazar presupuestos.', 'error')
        return redirect(request.referrer or url_for('index'))

    db = get_db()
    quote = db.execute('SELECT ticket_id FROM presupuestos WHERE id = ?', (quote_id,)).fetchone()

    if quote is None:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(request.referrer or url_for('index'))

    try:
        db.execute('UPDATE presupuestos SET estado = ? WHERE id = ?', ('Rechazado', quote_id))
        db.commit()
        flash('Presupuesto rechazado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al rechazar el presupuesto: {e}', 'error')
        db.rollback()

    return redirect(url_for('jobs.view_job', job_id=quote['ticket_id']))