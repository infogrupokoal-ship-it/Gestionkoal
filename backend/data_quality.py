from backend.extensions import db
from backend.models import get_table_class
from sqlalchemy import func

def check_duplicate_materials():
    Material = get_table_class('materiales')
    duplicates = db.session.query(
        Material.nombre,
        Material.proveedor_id,
        func.count(Material.id)
    ).group_by(
        Material.nombre,
        Material.proveedor_id
    ).having(
        func.count(Material.id) > 1
    ).all()
    return duplicates

def check_services_without_price():
    Service = get_table_class('servicios')
    services_without_price = db.session.query(Service).filter(
        (Service.precio_base_estimado == None) | (Service.precio_base_estimado == 0)
    ).all()
    return services_without_price

def check_low_stock_materials():
    Material = get_table_class('materiales')
    low_stock_materials = db.session.query(Material).filter(
        Material.stock_actual <= Material.stock_minimo
    ).all()
    return low_stock_materials

def get_material_category_stats():
    Material = get_table_class('materiales')
    stats = db.session.query(
        Material.categoria,
        func.count(Material.id),
        func.sum(Material.stock_actual)
    ).group_by(
        Material.categoria
    ).all()
    return stats

def get_service_category_stats():
    Service = get_table_class('servicios')
    stats = db.session.query(
        Service.categoria,
        func.count(Service.id),
        func.avg(Service.precio_base_estimado)
    ).group_by(
        Service.categoria
    ).all()
    return stats

def get_average_material_usage_per_ticket():
    JobMaterial = get_table_class('job_materials')
    Ticket = get_table_class('tickets')

    # Contar el número total de tickets
    total_tickets = db.session.query(func.count(Ticket.id)).scalar()
    if total_tickets == 0:
        return 0

    # Sumar la cantidad total de materiales usados en todos los tickets
    total_materials_used = db.session.query(func.sum(JobMaterial.quantity)).scalar()
    if total_materials_used is None:
        total_materials_used = 0

    return total_materials_used / total_tickets
