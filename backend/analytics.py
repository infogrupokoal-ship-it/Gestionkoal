from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from backend.extensions import db
from backend.models import get_table_class
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta

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

    results = db.session.query(
        Client.nombre,
        func.count(Ticket.id)
    ).join(
        Ticket, Ticket.cliente_id == Client.id
    ).group_by(
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

    results = db.session.query(
        Material.nombre,
        func.sum(JobMaterial.quantity)
    ).join(
        JobMaterial, JobMaterial.material_id == Material.id
    ).join(
        Ticket, JobMaterial.job_id == Ticket.id
    ).filter(
        Ticket.fecha_creacion >= three_months_ago.strftime('%Y-%m-%d')
    ).group_by(
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
    Gasto = get_table_class('gastos') # Asumiendo que existe una tabla 'gastos'
    User = get_table_class('users')

    # Gastos por categoría (si existe una columna de categoría en gastos)
    # Si no, se puede agrupar por descripción o por freelancer
    expenses_by_category = db.session.query(
        Gasto.descripcion, # Usamos la descripción como proxy de categoría
        func.sum(Gasto.importe)
    ).group_by(
        Gasto.descripcion
    ).order_by(
        func.sum(Gasto.importe).desc()
    ).limit(5).all()

    category_labels = [r[0] for r in expenses_by_category]
    category_data = [float(r[1]) for r in expenses_by_category]

    # Gastos por freelancer
    expenses_by_freelancer = db.session.query(
        User.username,
        func.sum(Gasto.importe)
    ).join(
        User, Gasto.creado_por == User.id
    ).filter(
        User.role == 'autonomo' # Asumiendo que los freelancers tienen el rol 'autonomo'
    ).group_by(
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