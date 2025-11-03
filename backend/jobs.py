import json
import os
from datetime import datetime
import uuid # Import uuid for unique filenames

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

from backend.extensions import db
from backend.market_study import get_market_study_for_material
from backend.models import get_table_class
from backend.whatsapp import WhatsAppClient
from backend.activity_log import add_activity_log
from backend.pricing import get_effective_rate

bp = Blueprint("jobs", __name__, url_prefix="/jobs")


from backend.models import get_table_class

# Helper function for image upload
def _handle_image_upload(file_storage):
    if file_storage and file_storage.filename != '':
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if '.' in file_storage.filename and \
           file_storage.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
            
            # Generate a unique filename
            extension = file_storage.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{extension}"

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, unique_filename)
            file_storage.save(file_path)
            return url_for('static', filename=f'uploads/{unique_filename}')
        else:
            raise ValueError("Tipo de archivo no permitido.")
    return None


def _create_job(cliente_id, autonomo_id, tipo, titulo, descripcion, estado, estado_pago, metodo_pago, presupuesto, vat_rate, fecha_visita, job_difficulty_rating, creado_por, imagen_url=None):
    Ticket = get_table_class("tickets")
    new_job = Ticket(
        cliente_id=cliente_id,
        asignado_a=autonomo_id,
        tipo=tipo,
        titulo=titulo,
        descripcion=descripcion,
        estado=estado,
        estado_pago=estado_pago,
        metodo_pago=metodo_pago,
        presupuesto=presupuesto,
        vat_rate=vat_rate,
        fecha_visita=fecha_visita,
        job_difficulty_rating=job_difficulty_rating,
        creado_por=creado_por,
        imagen_url=imagen_url,
    )
    db.session.add(new_job)
    db.session.flush()
    return new_job


def _send_job_notifications(job, client_name):
    from .notifications import add_notification, send_whatsapp_notification

    User = get_table_class("users")
    admin_users = db.session.query(User).filter(User.role == 'admin').all()

    notification_message = f"Nuevo trabajo añadido por {g.user.username}: {job.titulo} para {client_name}."

    add_notification(db.session, g.user.id, notification_message)
    send_whatsapp_notification(db.session, g.user.id, notification_message)

    for admin in admin_users:
        if admin.id != g.user.id:
            add_notification(db.session, admin.id, notification_message)
            send_whatsapp_notification(db.session, admin.id, notification_message)

    if job.asignado_a:
        freelancer_user = db.session.query(User).filter_by(id=job.asignado_a).first()
        if freelancer_user:
            freelancer_notification_message = f"Se te ha asignado un nuevo trabajo: {job.titulo} para {client_name}."
            add_notification(
                db.session,
                freelancer_user.id,
                freelancer_notification_message,
            )
            send_whatsapp_notification(
                db.session,
                freelancer_user.id,
                freelancer_notification_message,
            )


def _create_financial_transactions(job, form):
    if job.estado_pago == "Pagado":
        amount = float(job.presupuesto) if job.presupuesto else 0.0
        vat_rate_val = float(job.vat_rate) if job.vat_rate else 0.0
        vat_amount = amount * (vat_rate_val / 100)
        total_amount = amount + vat_amount
        FinancialTransaction = get_table_class("financial_transactions")
        new_transaction = FinancialTransaction(
            ticket_id=job.id,
            type="ingreso",
            vat_amount=vat_amount,
        )
        db.session.add(new_transaction)
        flash("Ingreso registrado en transacciones financieras.", "info")

    new_provision_fondos = (
        float(form.get("provision_fondos"))
        if form.get("provision_fondos")
        else 0.0
    )
    if new_provision_fondos > 0:
        FinancialTransaction = get_table_class("financial_transactions")
        new_transaction = FinancialTransaction(
            ticket_id=job.id,
            type="gasto",
            amount=new_provision_fondos,
            description=f"Provisión de fondos para trabajo {job.titulo}",
            recorded_by=g.user.id,
        )
        db.session.add(new_transaction)
        flash("Provisión de fondos registrada como gasto.", "info")


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_job():
    error = None
    Client = get_table_class("clientes")
    User = get_table_class("users")
    clients = db.session.query(Client).order_by(Client.nombre).all()
    autonomos = db.session.query(User).filter(User.role == 'autonomo').all()

    if request.method == "POST":
        cliente_id = request.form.get("client_id")
        autonomo_id = request.form.get("autonomo_id")
        if autonomo_id == "":
            autonomo_id = None

        tipo = request.form.get("tipo")
        titulo = request.form.get("titulo")
        descripcion = request.form.get("descripcion")
        estado = request.form.get("estado")
        estado_pago = request.form.get("estado_pago")
        metodo_pago = request.form.get("metodo_pago")
        presupuesto = request.form.get("presupuesto")
        vat_rate = request.form.get("vat_rate")
        fecha_visita = request.form.get("fecha_visita")
        job_difficulty_rating = request.form.get("job_difficulty_rating")
        creado_por = g.user.id if g.user.is_authenticated else 1
        imagen = request.files.get("imagen")

        if not cliente_id or not titulo or not tipo:
            error = "Cliente, Tipo y Título son obligatorios."

        if cliente_id:
            client_data = db.session.query(Client).filter_by(id=cliente_id).first()
            if client_data and client_data.is_ngo and metodo_pago != "Efectivo":
                error = "Las ONG sin ánimo de lucro deben pagar en efectivo."

        if error is not None:
            flash(error)
        else:
            try:
                imagen_url = _handle_image_upload(imagen)

                new_job = _create_job(
                    cliente_id,
                    autonomo_id,
                    tipo,
                    titulo,
                    descripcion,
                    estado,
                    estado_pago,
                    metodo_pago,
                    presupuesto,
                    vat_rate,
                    fecha_visita,
                    job_difficulty_rating,
                    creado_por,
                    imagen_url, # Pass the imagen_url
                )
                client_name = db.session.query(Client.nombre).filter_by(id=cliente_id).scalar()
                _send_job_notifications(new_job, client_name)
                _create_financial_transactions(new_job, request.form)

                add_activity_log('create_job', 'job', new_job.id, f'Trabajo creado para {client_name}')
                db.session.commit()
                flash("¡Trabajo añadido correctamente!")
                return redirect(url_for("jobs.list_jobs"))
            except Exception as e:
                db.session.rollback()
                error = f"Ocurrió un error inesperado: {e}"
                flash(error)

    trabajo = {}
    client_is_ngo = False
    all_clients_data = db.session.query(Client).all()
    clients_json = json.dumps([dict(c) for c in all_clients_data])

    if request.method == "GET" and request.args.get("client_id"):
        client_id = request.args.get("client_id", type=int)
        client_data = db.session.query(Client).filter_by(id=client_id).first()
        if client_data:
            client_is_ngo = client_data.is_ngo

    return render_template(
        "trabajos/form.html",
        title="Añadir Trabajo",
        trabajo=trabajo,
        clients=clients,
        autonomos=autonomos,
        candidate_autonomos=None,
        client_is_ngo=client_is_ngo,
        all_clients_data=clients_json,
    )


@bp.route("/")
@login_required
def list_jobs():
    try:
        Ticket = get_table_class("tickets")
        Client = get_table_class("clientes")
        User = get_table_class("users")
        Event = get_table_class("eventos")

        jobs = (
            db.session.query(
                Ticket.id,
                Ticket.descripcion,
                Ticket.estado,
                Ticket.prioridad,
                Ticket.tipo,
                Client.nombre.label("client_name"),
                User.username.label("assigned_to_name"),
                Event.inicio,
                Event.fin,
            )
            .outerjoin(Client, Ticket.cliente_id == Client.id)
            .outerjoin(User, Ticket.asignado_a == User.id)
            .outerjoin(Event, Ticket.id == Event.ticket_id)
            .order_by(Ticket.fecha_creacion.desc())
            .all()
        )
        return render_template("trabajos/list.html", jobs=jobs)
    except Exception as e:
        current_app.logger.error(f"Error al listar los trabajos: {e}", exc_info=True)
        flash("Ocurrió un error al cargar los trabajos.", "error")
        return redirect(url_for("index"))


@bp.route("/<int:job_id>")
@login_required
def view_job(job_id):
    try:
        Ticket = get_table_class("tickets")
        Client = get_table_class("clientes")
        User = get_table_class("users")
        JobService = get_table_class("job_services")
        Service = get_table_class("services")
        JobMaterial = get_table_class("job_materials")
        Material = get_table_class("materiales")
        Provider = get_table_class("providers")
        ProviderQuote = get_table_class("provider_quotes")
        Presupuesto = get_table_class("presupuestos")

        job = (
            db.session.query(
                Ticket,
                Client.nombre.label("client_name"),
                Client.telefono.label("client_phone"),
                Client.email.label("client_email"),
                User.username.label("assigned_user_name"),
                User.email.label("assigned_user_email"),
            )
            .outerjoin(Client, Ticket.cliente_id == Client.id)
            .outerjoin(User, Ticket.asignado_a == User.id)
            .filter(Ticket.id == job_id)
            .first()
        )

        if job is None:
            flash("Trabajo no encontrado.", "error")
            return redirect(url_for("jobs.list_jobs"))

        services = (
            db.session.query(
                JobService.service_id,
                Service.name,
                Service.description,
                JobService.quantity,
                JobService.price_per_unit,
                JobService.total_price,
            )
            .join(Service, JobService.service_id == Service.id)
            .filter(JobService.job_id == job_id)
            .all()
        )

        materials = (
            db.session.query(
                JobMaterial.material_id,
                Material.nombre,
                Material.sku,
                JobMaterial.quantity,
                JobMaterial.price_per_unit,
                JobMaterial.total_price,
            )
            .join(Material, JobMaterial.material_id == Material.id)
            .filter(JobMaterial.job_id == job_id)
            .all()
        )

        providers = db.session.query(Provider).order_by(Provider.nombre).all()

        existing_quotes = (
            db.session.query(
                ProviderQuote.id,
                ProviderQuote.material_id,
                ProviderQuote.provider_id,
                Provider.nombre.label("provider_name"),
                ProviderQuote.quote_amount,
                ProviderQuote.status,
                ProviderQuote.quote_date,
                ProviderQuote.payment_status,
                ProviderQuote.payment_date,
            )
            .join(Provider, ProviderQuote.provider_id == Provider.id)
            .filter(ProviderQuote.job_id == job_id)
            .order_by(ProviderQuote.quote_date.desc())
            .all()
        )

        quotes_by_material = {}
        for quote in existing_quotes:
            if quote.material_id not in quotes_by_material:
                quotes_by_material[quote.material_id] = []
            quotes_by_material[quote.material_id].append(quote)

        materials_with_market_study = []
        for material in materials:
            material_dict = dict(material._asdict())
            market_study_data = get_market_study_for_material(material.material_id)
            material_dict["market_study"] = market_study_data
            materials_with_market_study.append(material_dict)

        freelancer_quotes = (
            db.session.query(
                Presupuesto.id,
                Presupuesto.total,
                Presupuesto.estado,
                Presupuesto.fecha_creacion,
                Presupuesto.billing_entity_type,
                Presupuesto.billing_entity_id,
                User.username.label("freelancer_name"),
            )
            .join(User, Presupuesto.freelancer_id == User.id)
            .filter(Presupuesto.ticket_id == job_id, Presupuesto.freelancer_id != None)
            .order_by(Presupuesto.fecha_creacion.desc())
            .all()
        )

        Fichero = get_table_class("ficheros")
        ActivityLog = get_table_class("actividad_log")
        freelancer_quotes_with_files = []
        for f_quote in freelancer_quotes:
            f_quote_dict = dict(f_quote._asdict())
            files = (
                db.session.query(Fichero.id, Fichero.url, Fichero.tipo)
                .filter(Fichero.presupuesto_id == f_quote.id)
                .all()
            )
            f_quote_dict["files"] = files
            freelancer_quotes_with_files.append(f_quote_dict)

        activity_log = db.session.query(ActivityLog).filter_by(entity_id=job_id, entity_type='job').order_by(ActivityLog.timestamp.desc()).all()

        return render_template(
            "jobs/view.html",
            job=job,
            services=services,
            materials=materials_with_market_study,
            providers=providers,
            quotes_by_material=quotes_by_material,
            freelancer_quotes=freelancer_quotes_with_files,
            activity_log=activity_log,
        )

    except Exception as e:
        current_app.logger.error(f"Error in view_job: {e}", exc_info=True)
        return "Ocurrió un error interno en el servidor.", 500


def _update_job(job, form, imagen_url=None):
    job.cliente_id = form.get("client_id", type=int)
    job.asignado_a = form.get("autonomo_id", type=int)
    if job.asignado_a == 0:
        job.asignado_a = None
    job.tipo = form.get("tipo")
    job.titulo = form.get("titulo")
    job.descripcion = form.get("descripcion")
    job.estado = form.get("estado")
    job.estado_pago = form.get("estado_pago")
    job.metodo_pago = form.get("metodo_pago")
    job.presupuesto = form.get("presupuesto", type=float)
    job.vat_rate = form.get("vat_rate", type=float)
    job.fecha_visita = form.get("fecha_visita")
    job.job_difficulty_rating = form.get("job_difficulty_rating", type=int)
    if imagen_url:
        job.imagen_url = imagen_url
    return job


def _handle_receipt_upload(job, files):
    if "receipt_photo" in files:
        receipt_photo = files["receipt_photo"]
        if receipt_photo.filename != "":
            allowed_extensions = {"png", "jpg", "jpeg", "gif", "pdf"}
            if (
                "." in receipt_photo.filename
                and receipt_photo.filename.rsplit(".", 1)[1].lower()
                in allowed_extensions
            ):
                filename = secure_filename(
                    f"{job.id}_receipt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{receipt_photo.filename}"
                )
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                receipt_photo.save(file_path)
                job.recibo_url = url_for("static", filename=f'uploads/{filename}')
            else:
                raise ValueError("Tipo de archivo no permitido para el recibo.")
    return job


def _send_job_update_notifications(job, original_estado, original_estado_pago):
    Client = get_table_class("clientes")
    client_info = db.session.query(Client).filter_by(id=job.cliente_id).first()
    client = WhatsAppClient()

    if job.estado != original_estado:
        msg = f"El estado de su trabajo '{job.titulo}' ha cambiado a '{job.estado}'."
        if client_info and client_info.whatsapp_opt_in:
            client.send_text(client_info.whatsapp_number, msg)

    if job.estado_pago != original_estado_pago:
        msg = f"El estado de pago de su trabajo '{job.titulo}' ha cambiado a '{job.estado_pago}'."
        if client_info and client_info.whatsapp_opt_in:
            client.send_text(client_info.whatsapp_number, msg)


def _create_financial_transactions_on_payment(job):
    if job.estado_pago == "Pagado":
        amount = float(job.presupuesto) if job.presupuesto else 0.0
        vat_rate_val = float(job.vat_rate) if job.vat_rate else 0.0
        vat_amount = amount * (vat_rate_val / 100)
        total_amount = amount + vat_amount
        FinancialTransaction = get_table_class("financial_transactions")
        new_transaction = FinancialTransaction(
            ticket_id=job.id,
            type="income",
            amount=total_amount,
            description=f"Pago de trabajo {job.titulo}",
            recorded_by=g.user.id,
            vat_rate=job.vat_rate,
            vat_amount=vat_amount,
        )
        db.session.add(new_transaction)
        flash("Ingreso registrado en transacciones financieras.", "info")

        from backend.receipt_generator import generate_receipt_pdf

        pdf_filename = (
            f"recibo_{job.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        )
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        pdf_filepath = os.path.join(upload_folder, pdf_filename)

        job_details_for_pdf = {
            "id": job.id,
            "description": job.descripcion,
            "status": job.estado,
            "payment_method": job.metodo_pago,
            "payment_status": job.estado_pago,
            "amount": total_amount,
        }
        Client = get_table_class("clientes")
        client_details_for_pdf = db.session.query(Client).filter_by(id=job.cliente_id).first()
        company_details = {
            "name": "Grupo Koal",
            "address": "Valencia, España",
            "phone": "N/A",
            "email": "info@grupokoal.com",
        }

        generate_receipt_pdf(
            output_path=pdf_filepath,
            job_details=job_details_for_pdf,
            client_details=client_details_for_pdf.__dict__,
            company_details=company_details,
        )

        pdf_url = url_for("static", filename=f'uploads/{pdf_filename}')
        job.recibo_url = pdf_url
        flash("Recibo PDF generado y guardado.", "success")


@bp.route("/<int:job_id>/edit", methods=("GET", "POST"))
@login_required
def edit_job(job_id):
    try:
        Ticket = get_table_class("tickets")
        job = db.session.query(Ticket).filter_by(id=job_id).first()

        if job is None:
            flash("Trabajo no encontrado.", "error")
            return redirect(url_for("jobs.list_jobs"))

        original_estado = job.estado
        original_estado_pago = job.estado_pago

        if request.method == "POST":
            try:
                imagen_file = request.files.get("imagen")
                imagen_url = None
                if imagen_file:
                    imagen_url = _handle_image_upload(imagen_file)

                job = _update_job(job, request.form, imagen_url)
                job = _handle_receipt_upload(job, request.files)
                _send_job_update_notifications(job, original_estado, original_estado_pago)
                if job.estado != original_estado:
                    add_activity_log('update_job_status', 'job', job_id, f'Estado cambiado de {original_estado} a {job.estado}')
                if job.estado_pago != original_estado_pago:
                    add_activity_log('update_payment_status', 'job', job_id, f'Estado de pago cambiado de {original_estado_pago} a {job.estado_pago}')

                if job.estado_pago == "Pagado" and original_estado_pago != "Pagado":
                    _create_financial_transactions_on_payment(job)

                db.session.commit()
                flash("¡Trabajo actualizado correctamente!", "success")
                return redirect(url_for("jobs.list_jobs"))
            except ValueError as e:
                flash(str(e), "error")
                db.session.rollback()
            except Exception as e:
                db.session.rollback()
                flash(f"Ocurrió un error inesperado: {e}", "error")
                current_app.logger.error(f"Error al actualizar el trabajo {job_id}: {e}", exc_info=True)
        
        # This part handles GET requests or re-renders the form after a POST error
        Client = get_table_class("clientes")
        User = get_table_class("users")
        Gasto = get_table_class("gastos_compartidos")
        Tarea = get_table_class("ticket_tareas")

        clients = db.session.query(Client).order_by(Client.nombre).all()
        autonomos = db.session.query(User).filter(User.role == 'autonomo').all()
        gastos = db.session.query(Gasto).filter_by(ticket_id=job_id).order_by(Gasto.fecha.desc()).all()
        tareas = db.session.query(Tarea).filter_by(ticket_id=job_id).order_by(Tarea.created_at.desc()).all()

        # --- Suggestion Engine ---
        candidate_autonomos = []
        if job.tipo:
            Freelancer = get_table_class("freelancers")
            candidate_autonomos = (
                db.session.query(User)
                .join(Freelancer, User.id == Freelancer.user_id)
                .filter(User.role == 'autonomo')
                .filter(
                    (Freelancer.category.like(f'%{job.tipo}%')) |
                    (Freelancer.specialty.like(f'%{job.tipo}%'))
                )
                .all()
            )
        # --- End Suggestion Engine ---

        return render_template(
            "trabajos/form.html",
            title="Editar Trabajo",
            trabajo=job,
            clients=clients,
            autonomos=autonomos,
            gastos=gastos,
            tareas=tareas,
            candidate_autonomos=candidate_autonomos,
        )
    except Exception as e:
        current_app.logger.error(f"Error al editar el trabajo: {e}", exc_info=True)
        flash(f"Ocurrió un error interno en el servidor al cargar el trabajo: {e}", "error")
        return redirect(url_for("jobs.list_jobs"))
