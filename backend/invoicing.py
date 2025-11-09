from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import text, func

from backend.extensions import db
from backend.models import get_table_class
# from backend.pdf_utils import generate_invoice_pdf # Asumiendo que existe o se creará

invoicing_bp = Blueprint('invoicing', __name__, url_prefix='/invoicing')

@invoicing_bp.route('/')
@login_required
def list_invoices():
    if not current_user.has_permission('view_invoices'):
        flash('No tienes permiso para ver facturas.', 'error')
        return redirect(url_for('index'))

    Factura = get_table_class('facturas')
    Client = get_table_class('clientes')
    Ticket = get_table_class('tickets')

    query = db.session.query(
        Factura.id,
        Factura.fecha_emision,
        Factura.fecha_vencimiento,
        Factura.total_neto,
        Factura.estado,
        Client.nombre.label('client_name'),
        Ticket.titulo.label('job_title')
    ).join(Client, Factura.client_id == Client.id) \
     .outerjoin(Ticket, Factura.ticket_id == Ticket.id)

    # Implementar filtrado por rol si es necesario (ej. comercial solo ve facturas de sus clientes)
    # if current_user.has_role('comercial'):
    #     query = query.filter(Client.referred_by_partner_id == current_user.id)

    facturas = query.order_by(Factura.fecha_emision.desc()).all()

    return render_template('invoicing/list.html', invoices=facturas)

@invoicing_bp.route('/create_from_job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def create_invoice_from_job(job_id):
    if not current_user.has_permission('create_invoices'):
        flash('No tienes permiso para crear facturas.', 'error')
        return redirect(url_for('jobs.view_job', job_id=job_id))

    Ticket = get_table_class('tickets')
    Client = get_table_class('clientes')
    Factura = get_table_class('facturas')

    job = db.session.query(Ticket).filter_by(id=job_id).first()
    if not job:
        flash('Trabajo no encontrado.', 'error')
        return redirect(url_for('jobs.list_jobs'))

    client = db.session.query(Client).filter_by(id=job.cliente_id).first()
    if not client:
        flash('Cliente asociado al trabajo no encontrado.', 'error')
        return redirect(url_for('jobs.view_job', job_id=job_id))

    if request.method == 'POST':
        try:
            # Calcular totales de la factura
            total_bruto = float(job.presupuesto) if job.presupuesto else 0.0
            vat_rate = float(job.vat_rate) if job.vat_rate else 0.0
            total_iva = total_bruto * (vat_rate / 100)
            total_neto = total_bruto + total_iva

            new_invoice = Factura(
                ticket_id=job.id,
                client_id=client.id,
                fecha_emision=datetime.now().date(),
                fecha_vencimiento=datetime.now().date(), # Se puede ajustar en el formulario
                total_bruto=total_bruto,
                total_iva=total_iva,
                total_neto=total_neto,
                estado='emitida' # O 'borrador'
            )
            db.session.add(new_invoice)
            db.session.commit()

            # Generar PDF de la factura
            # pdf_filename = f"factura_{new_invoice.id}.pdf"
            # pdf_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], pdf_filename)
            # generate_invoice_pdf(new_invoice, client, job, pdf_filepath) # Función a implementar
            # new_invoice.pdf_url = url_for('uploaded_file', filename=pdf_filename)
            # db.session.commit()

            flash('Factura creada correctamente.', 'success')
            return redirect(url_for('invoicing.list_invoices'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la factura: {e}', 'error')

    return render_template('invoicing/create_from_job.html', job=job, client=client, today=datetime.now().date())

@invoicing_bp.route('/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    if not current_user.has_permission('view_invoices'):
        flash('No tienes permiso para ver facturas.', 'error')
        return redirect(url_for('index'))

    Factura = get_table_class('facturas')
    Client = get_table_class('clientes')
    Ticket = get_table_class('tickets')

    invoice = db.session.query(
        Factura,
        Client.nombre.label('client_name'),
        Client.nif.label('client_nif'),
        Client.email.label('client_email'),
        Ticket.titulo.label('job_title')
    ).join(Client, Factura.client_id == Client.id) \
     .outerjoin(Ticket, Factura.ticket_id == Ticket.id) \
     .filter(Factura.id == invoice_id).first()

    if not invoice:
        flash('Factura no encontrada.', 'error')
        return redirect(url_for('invoicing.list_invoices'))

    return render_template('invoicing/view.html', invoice=invoice)

@invoicing_bp.route('/<int:invoice_id>/mark_as_paid', methods=['POST'])
@login_required
def mark_invoice_as_paid(invoice_id):
    if not current_user.has_permission('manage_invoices'):
        flash('No tienes permiso para gestionar facturas.', 'error')
        return redirect(url_for('invoicing.list_invoices'))

    Factura = get_table_class('facturas')
    invoice = db.session.query(Factura).filter_by(id=invoice_id).first()

    if not invoice:
        flash('Factura no encontrada.', 'error')
        return redirect(url_for('invoicing.list_invoices'))

    try:
        invoice.estado = 'pagada'
        invoice.updated_at = datetime.now()
        db.session.commit()
        flash('Factura marcada como pagada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al marcar factura como pagada: {e}', 'error')
    
    return redirect(url_for('invoicing.view_invoice', invoice_id=invoice_id))

# Rutas para partes de horas
@invoicing_bp.route('/time_sheets')
@login_required
def list_time_sheets():
    if not current_user.has_permission('view_time_sheets'):
        flash('No tienes permiso para ver partes de horas.', 'error')
        return redirect(url_for('index'))

    ParteHoras = get_table_class('partes_horas')
    User = get_table_class('users')
    Ticket = get_table_class('tickets')

    query = db.session.query(
        ParteHoras.id,
        ParteHoras.fecha,
        ParteHoras.horas_trabajadas,
        ParteHoras.descripcion,
        ParteHoras.costo_total,
        User.username.label('user_name'),
        Ticket.titulo.label('job_title')
    ).join(User, ParteHoras.user_id == User.id) \
     .join(Ticket, ParteHoras.ticket_id == Ticket.id)

    # Filtrar por usuario si no es admin
    if not current_user.has_permission('manage_time_sheets'):
        query = query.filter(ParteHoras.user_id == current_user.id)

    time_sheets = query.order_by(ParteHoras.fecha.desc()).all()

    return render_template('invoicing/time_sheets_list.html', time_sheets=time_sheets)

@invoicing_bp.route('/time_sheets/add/<int:job_id>', methods=['GET', 'POST'])
@login_required
def add_time_sheet(job_id):
    if not current_user.has_permission('add_time_sheets'):
        flash('No tienes permiso para añadir partes de horas.', 'error')
        return redirect(url_for('jobs.view_job', job_id=job_id))

    Ticket = get_table_class('tickets')
    job = db.session.query(Ticket).filter_by(id=job_id).first()
    if not job:
        flash('Trabajo no encontrado.', 'error')
        return redirect(url_for('jobs.list_jobs'))

    if request.method == 'POST':
        try:
            fecha = request.form['fecha']
            horas_trabajadas = float(request.form['horas_trabajadas'])
            descripcion = request.form.get('descripcion')
            tarifa_hora = float(request.form.get('tarifa_hora', 0.0))
            costo_total = horas_trabajadas * tarifa_hora

            ParteHoras = get_table_class('partes_horas')
            new_time_sheet = ParteHoras(
                ticket_id=job_id,
                user_id=current_user.id,
                fecha=datetime.strptime(fecha, '%Y-%m-%d').date(),
                horas_trabajadas=horas_trabajadas,
                descripcion=descripcion,
                tarifa_hora=tarifa_hora,
                costo_total=costo_total
            )
            db.session.add(new_time_sheet)
            db.session.commit()
            flash('Parte de horas añadido correctamente.', 'success')
            return redirect(url_for('jobs.view_job', job_id=job_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al añadir parte de horas: {e}', 'error')

    return render_template('invoicing/time_sheet_form.html', job=job, today=datetime.now().date())

@invoicing_bp.route('/time_sheets/edit/<int:time_sheet_id>', methods=['GET', 'POST'])
@login_required
def edit_time_sheet(time_sheet_id):
    ParteHoras = get_table_class('partes_horas')
    time_sheet = db.session.query(ParteHoras).filter_by(id=time_sheet_id).first()

    if not time_sheet:
        flash('Parte de horas no encontrado.', 'error')
        return redirect(url_for('invoicing.list_time_sheets'))

    if not current_user.has_permission('edit_time_sheets') and time_sheet.user_id != current_user.id:
        flash('No tienes permiso para editar este parte de horas.', 'error')
        return redirect(url_for('invoicing.list_time_sheets'))

    if request.method == 'POST':
        try:
            time_sheet.fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()
            time_sheet.horas_trabajadas = float(request.form['horas_trabajadas'])
            time_sheet.descripcion = request.form.get('descripcion')
            time_sheet.tarifa_hora = float(request.form.get('tarifa_hora', 0.0))
            time_sheet.costo_total = time_sheet.horas_trabajadas * time_sheet.tarifa_hora
            time_sheet.updated_at = datetime.now()
            db.session.commit()
            flash('Parte de horas actualizado correctamente.', 'success')
            return redirect(url_for('jobs.view_job', job_id=time_sheet.ticket_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar parte de horas: {e}', 'error')

    return render_template('invoicing/time_sheet_form.html', time_sheet=time_sheet)

@invoicing_bp.route('/time_sheets/delete/<int:time_sheet_id>', methods=['POST'])
@login_required
def delete_time_sheet(time_sheet_id):
    ParteHoras = get_table_class('partes_horas')
    time_sheet = db.session.query(ParteHoras).filter_by(id=time_sheet_id).first()

    if not time_sheet:
        flash('Parte de horas no encontrado.', 'error')
        return redirect(url_for('invoicing.list_time_sheets'))

    if not current_user.has_permission('delete_time_sheets') and time_sheet.user_id != current_user.id:
        flash('No tienes permiso para eliminar este parte de horas.', 'error')
        return redirect(url_for('invoicing.list_time_sheets'))

    try:
        db.session.delete(time_sheet)
        db.session.commit()
        flash('Parte de horas eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar parte de horas: {e}', 'error')
    
    return redirect(url_for('jobs.view_job', job_id=time_sheet.ticket_id))

# Rutas para liquidaciones
@invoicing_bp.route('/liquidations')
@login_required
def list_liquidations():
    if not current_user.has_permission('view_liquidations'):
        flash('No tienes permiso para ver liquidaciones.', 'error')
        return redirect(url_for('index'))

    Liquidacion = get_table_class('liquidaciones')
    User = get_table_class('users')

    query = db.session.query(
        Liquidacion.id,
        Liquidacion.fecha_liquidacion,
        Liquidacion.periodo_inicio,
        Liquidacion.periodo_fin,
        Liquidacion.monto_total,
        Liquidacion.estado,
        User.username.label('autonomo_name')
    ).join(User, Liquidacion.autonomo_id == User.id)

    # Filtrar por autónomo si no es admin
    if current_user.has_role('autonomo'):
        query = query.filter(Liquidacion.autonomo_id == current_user.id)
    elif not current_user.has_permission('manage_liquidations'):
        flash('No tienes permiso para ver todas las liquidaciones.', 'error')
        return redirect(url_for('index'))

    liquidations = query.order_by(Liquidacion.fecha_liquidacion.desc()).all()

    return render_template('invoicing/liquidations_list.html', liquidations=liquidations)

@invoicing_bp.route('/liquidations/generate', methods=['GET', 'POST'])
@login_required
def generate_liquidacion():
    if not current_user.has_permission('generate_liquidations'):
        flash('No tienes permiso para generar liquidaciones.', 'error')
        return redirect(url_for('invoicing.list_liquidations'))

    User = get_table_class('users')
    autonomos = db.session.query(User).filter_by(role='autonomo').order_by(User.username).all()

    if request.method == 'POST':
        try:
            autonomo_id = request.form['autonomo_id']
            periodo_inicio_str = request.form['periodo_inicio']
            periodo_fin_str = request.form['periodo_fin']

            periodo_inicio = datetime.strptime(periodo_inicio_str, '%Y-%m-%d').date()
            periodo_fin = datetime.strptime(periodo_fin_str, '%Y-%m-%d').date()

            # Calcular monto total de la liquidación
            ParteHoras = get_table_class('partes_horas')
            total_horas_costo = db.session.query(func.sum(ParteHoras.costo_total)).filter(
                ParteHoras.user_id == autonomo_id,
                ParteHoras.fecha >= periodo_inicio,
                ParteHoras.fecha <= periodo_fin
            ).scalar() or 0.0

            # Aquí se podrían añadir otros conceptos (ej. comisiones, gastos reembolsables)
            monto_total = total_horas_costo

            Liquidacion = get_table_class('liquidaciones')
            new_liquidacion = Liquidacion(
                autonomo_id=autonomo_id,
                fecha_liquidacion=datetime.now().date(),
                periodo_inicio=periodo_inicio,
                periodo_fin=periodo_fin,
                monto_total=monto_total,
                estado='pendiente'
            )
            db.session.add(new_liquidacion)
            db.session.commit()
            flash('Liquidación generada correctamente.', 'success')
            return redirect(url_for('invoicing.list_liquidations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al generar liquidación: {e}', 'error')

    return render_template('invoicing/liquidacion_form.html', autonomos=autonomos, today=datetime.now().date())

@invoicing_bp.route('/liquidations/<int:liquidacion_id>')
@login_required
def view_liquidacion(liquidacion_id):
    if not current_user.has_permission('view_liquidations'):
        flash('No tienes permiso para ver liquidaciones.', 'error')
        return redirect(url_for('index'))

    Liquidacion = get_table_class('liquidaciones')
    User = get_table_class('users')
    ParteHoras = get_table_class('partes_horas')
    Ticket = get_table_class('tickets')

    liquidacion = db.session.query(
        Liquidacion,
        User.username.label('autonomo_name')
    ).join(User, Liquidacion.autonomo_id == User.id) \
     .filter(Liquidacion.id == liquidacion_id).first()

    if not liquidacion:
        flash('Liquidación no encontrada.', 'error')
        return redirect(url_for('invoicing.list_liquidations'))

    # Filtrar por autónomo si no es admin
    if current_user.has_role('autonomo') and liquidacion.Liquidacion.autonomo_id != current_user.id:
        flash('No tienes permiso para ver esta liquidación.', 'error')
        return redirect(url_for('invoicing.list_liquidations'))

    partes_horas_asociados = db.session.query(
        ParteHoras,
        Ticket.titulo.label('job_title')
    ).join(Ticket, ParteHoras.ticket_id == Ticket.id) \
     .filter(
        ParteHoras.user_id == liquidacion.Liquidacion.autonomo_id,
        ParteHoras.fecha >= liquidacion.Liquidacion.periodo_inicio,
        ParteHoras.fecha <= liquidacion.Liquidacion.periodo_fin
    ).order_by(ParteHoras.fecha.desc()).all()

    return render_template('invoicing/liquidacion_view.html', liquidacion=liquidacion, partes_horas_asociados=partes_horas_asociados)

@invoicing_bp.route('/liquidations/<int:liquidacion_id>/mark_as_paid', methods=['POST'])
@login_required
def mark_liquidacion_as_paid(liquidacion_id):
    if not current_user.has_permission('manage_liquidations'):
        flash('No tienes permiso para gestionar liquidaciones.', 'error')
        return redirect(url_for('invoicing.list_liquidations'))

    Liquidacion = get_table_class('liquidaciones')
    liquidacion = db.session.query(Liquidacion).filter_by(id=liquidacion_id).first()

    if not liquidacion:
        flash('Liquidación no encontrada.', 'error')
        return redirect(url_for('invoicing.list_liquidations'))

    try:
        liquidacion.estado = 'pagada'
        liquidacion.updated_at = datetime.now()
        db.session.commit()
        flash('Liquidación marcada como pagada.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al marcar liquidación como pagada: {e}', 'error')
    
    return redirect(url_for('invoicing.view_liquidacion', liquidacion_id=liquidacion_id))
