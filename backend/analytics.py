from datetime import datetime, timedelta

from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from sqlalchemy import func

from backend.extensions import db
from backend.models import get_table_class

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

@analytics_bp.route('/services_by_category')
@login_required
def services_by_category():
    if not current_user.has_permission('view_analytics'):
        return jsonify(error='Permiso denegado'), 403
    Service = get_table_class('servicios')
    JobService = get_table_class('job_services')

    results = db.session.query(
        Service.categoria,
        func.count(JobService.service_id)
    ).join(
        JobService, JobService.service_id == Service.id
    ).group_by(
        Service.categoria
    ).order_by(
        func.count(JobService.service_id).desc()
    ).all()

    labels = [r[0] or "Sin Categoría" for r in results]
    data = [r[1] for r in results]
    return jsonify(labels=labels, data=data)

@analytics_bp.route('/top_clients')
@login_required
def top_clients():
    if not current_user.has_permission('view_analytics'):
        return jsonify(error='Permiso denegado'), 403
    Client = get_table_class('clientes')
    Ticket = get_table_class('tickets')

    query = db.session.query(
        Client.nombre,
        func.count(Ticket.id)
    ).join(
        Ticket, Ticket.cliente_id == Client.id
    )

    if current_user.has_role('comercial'):
        query = query.filter(Client.referred_by_partner_id == current_user.id)

    results = query.group_by(
        Client.nombre
    ).order_by(
        func.count(Ticket.id).desc()
    ).limit(5).all()

    labels = [r[0] for r in results]
    data = [r[1] for r in results]
    return jsonify(labels=labels, data=data)

@analytics_bp.route('/jobs_by_status')
@login_required
def jobs_by_status():
    if not current_user.has_permission('view_analytics'):
        return jsonify(error='Permiso denegado'), 403
    Ticket = get_table_class('tickets')

    results = db.session.query(
        Ticket.estado,
        func.count(Ticket.id)
    ).group_by(
        Ticket.estado
    ).order_by(
        Ticket.estado
    ).all()

    labels = [r[0] for r in results]
    data = [r[1] for r in results]
    return jsonify(labels=labels, data=data)

@analytics_bp.route('/most_used_materials')
@login_required
def most_used_materials():
    if not current_user.has_permission('view_analytics'):
        return jsonify(error='Permiso denegado'), 403
    Material = get_table_class('materiales')
    JobMaterial = get_table_class('job_materials')
    Ticket = get_table_class('tickets')

    three_months_ago = datetime.now() - timedelta(days=90)

    query = db.session.query(
        Material.nombre,
        func.sum(JobMaterial.quantity)
    ).join(
        JobMaterial, JobMaterial.material_id == Material.id
    ).join(
        Ticket, JobMaterial.job_id == Ticket.id
    ).filter(
        Ticket.fecha_creacion >= three_months_ago.strftime('%Y-%m-%d')
    )

    if current_user.has_role('comercial'):
        query = query.filter(Ticket.comercial_id == current_user.id)

    results = query.group_by(
        Material.nombre
    ).order_by(
        func.sum(JobMaterial.quantity).desc()
    ).limit(5).all()

    labels = [r[0] for r in results]
    data = [float(r[1]) for r in results]
    return jsonify(labels=labels, data=data)

@analytics_bp.route('/expenses_by_category_freelancer')
@login_required
def expenses_by_category_freelancer():
    if not current_user.has_permission('view_analytics'):
        return jsonify(error='Permiso denegado'), 403
    Gasto = get_table_class('gastos')
    User = get_table_class('users')
    Ticket = get_table_class('tickets') # Import Ticket model

    # Gastos por categoría
    category_query = db.session.query(
        Gasto.descripcion,
        func.sum(Gasto.importe)
    ).join(
        Ticket, Gasto.ticket_id == Ticket.id # Join with Ticket
    )

    if current_user.has_role('comercial'):
        category_query = category_query.filter(Ticket.comercial_id == current_user.id)

    expenses_by_category = category_query.group_by(
        Gasto.descripcion
    ).order_by(
        func.sum(Gasto.importe).desc()
    ).limit(5).all()

    category_labels = [r[0] for r in expenses_by_category]
    category_data = [float(r[1]) for r in expenses_by_category]

    # Gastos por freelancer
    freelancer_query = db.session.query(
        User.username,
        func.sum(Gasto.importe)
    ).join(
        User, Gasto.creado_por == User.id
    ).join(
        Ticket, Gasto.ticket_id == Ticket.id # Join with Ticket
    ).filter(
        User.role == 'autonomo'
    )

    if current_user.has_role('comercial'):
        freelancer_query = freelancer_query.filter(Ticket.comercial_id == current_user.id)

    expenses_by_freelancer = freelancer_query.group_by(
        User.username
    ).order_by(
        func.sum(Gasto.importe).desc()
    ).limit(5).all()

    freelancer_labels = [r[0] for r in expenses_by_freelancer]
    freelancer_data = [float(r[1]) for r in expenses_by_freelancer]

    return jsonify(
        expenses_by_category={'labels': category_labels, 'data': category_data},
        expenses_by_freelancer={'labels': freelancer_labels, 'data': freelancer_data}
    )
