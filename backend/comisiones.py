from flask import Blueprint, flash, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import text

from backend.extensions import db
from backend.models import get_table_class

comisiones_bp = Blueprint('comisiones', __name__, url_prefix='/comisiones')

@comisiones_bp.route('/')
@login_required
def list_comisiones():
    if not current_user.has_permission('view_own_commissions') and not current_user.has_permission('manage_commissions'):
        flash('No tienes permiso para ver esta sección.', 'error')
        return redirect(url_for('index'))

    Comision = get_table_class('comisiones')
    User = get_table_class('users')
    Ticket = get_table_class('tickets')
    Client = get_table_class('clientes')

    query = db.session.query(
        Comision.id,
        Comision.monto_comision,
        Comision.porcentaje,
        Comision.estado,
        Comision.fecha_generacion,
        User.username.label('comercial_name'),
        Ticket.titulo.label('job_title'),
        Client.nombre.label('client_name')
    ).join(User, Comision.socio_comercial_id == User.id) \
     .outerjoin(Ticket, Comision.ticket_id == Ticket.id) \
     .outerjoin(Client, Ticket.cliente_id == Client.id)

    if current_user.has_role('comercial'):
        query = query.filter(Comision.socio_comercial_id == current_user.id)
    elif not current_user.has_permission('manage_commissions'): # If not admin and not comercial, or just not manage_commissions
        flash('No tienes permiso para ver todas las comisiones.', 'error')
        return redirect(url_for('index'))

    comisiones = query.order_by(Comision.fecha_generacion.desc()).all()

    return render_template('comisiones/list.html', comisiones=comisiones)

@comisiones_bp.route('/<int:comision_id>/mark_as_paid', methods=('POST',))
@login_required
def mark_comision_as_paid(comision_id):
    if not current_user.has_permission('manage_commissions'):
        flash('No tienes permiso para marcar comisiones como pagadas.', 'error')
        return redirect(url_for('comisiones.list_comisiones'))

    Comision = get_table_class('comisiones')
    comision = db.session.query(Comision).filter_by(id=comision_id).first()

    if comision is None:
        flash('Comisión no encontrada.', 'error')
        return redirect(url_for('comisiones.list_comisiones'))

    try:
        comision.estado = 'pagada'
        comision.fecha_pago = datetime.now()
        db.session.commit()
        flash('Comisión marcada como pagada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ocurrió un error al marcar la comisión como pagada: {e}', 'error')
    
    return redirect(url_for('comisiones.list_comisiones'))

@comisiones_bp.route('/api/comisiones', methods=('GET',))
@login_required
def api_list_comisiones():
    if not current_user.has_permission('view_own_commissions') and not current_user.has_permission('manage_commissions'):
        return jsonify({"error": "No tienes permiso para ver comisiones."}), 403

    Comision = get_table_class('comisiones')
    User = get_table_class('users')
    Ticket = get_table_class('tickets')
    Client = get_table_class('clientes')

    query = db.session.query(
        Comision.id,
        Comision.monto_comision,
        Comision.porcentaje,
        Comision.estado,
        Comision.fecha_generacion,
        User.username.label('comercial_name'),
        Ticket.titulo.label('job_title'),
        Client.nombre.label('client_name')
    ).join(User, Comision.socio_comercial_id == User.id) \
     .outerjoin(Ticket, Comision.ticket_id == Ticket.id) \
     .outerjoin(Client, Ticket.cliente_id == Client.id)

    if current_user.has_role('comercial'):
        query = query.filter(Comision.socio_comercial_id == current_user.id)
    elif not current_user.has_permission('manage_commissions'):
        return jsonify({"error": "No tienes permiso para ver todas las comisiones."}), 403

    comisiones = query.order_by(Comision.fecha_generacion.desc()).all()

    # Convertir resultados a una lista de diccionarios para jsonify
    comisiones_data = []
    for comision in comisiones:
        comisiones_data.append({
            "id": comision.id,
            "monto_comision": float(comision.monto_comision),
            "porcentaje": float(comision.porcentaje),
            "estado": comision.estado,
            "fecha_generacion": comision.fecha_generacion.isoformat() if comision.fecha_generacion else None,
            "comercial_name": comision.comercial_name,
            "job_title": comision.job_title,
            "client_name": comision.client_name
        })

    return jsonify(comisiones_data)
