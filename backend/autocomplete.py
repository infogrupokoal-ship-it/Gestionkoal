from flask import Blueprint, request, jsonify
from backend.db import get_db

bp = Blueprint('autocomplete', __name__, url_prefix='/autocomplete')

@bp.route('/clients')
def autocomplete_clients():
    query = request.args.get('q', '').strip()
    db = get_db()
    clients = db.execute(
        'SELECT id, nombre FROM clientes WHERE nombre LIKE ? ORDER BY nombre LIMIT 10',
        (f'%{query}%',)
    ).fetchall()
    return jsonify([dict(client) for client in clients])

@bp.route('/materials')
def autocomplete_materials():
    query = request.args.get('q', '').strip()
    db = get_db()
    materials = db.execute(
        'SELECT id, nombre, sku FROM materiales WHERE nombre LIKE ? OR sku LIKE ? ORDER BY nombre LIMIT 10',
        (f'%{query}%', f'%{query}%')
    ).fetchall()
    return jsonify([dict(material) for material in materials])

@bp.route('/services')
def autocomplete_services():
    query = request.args.get('q', '').strip()
    db = get_db()
    services = db.execute(
        'SELECT id, name, description FROM services WHERE name LIKE ? OR description LIKE ? ORDER BY name LIMIT 10',
        (f'%{query}%', f'%{query}%')
    ).fetchall()
    return jsonify([dict(service) for service in services])

@bp.route('/technicians_freelancers')
def autocomplete_technicians_freelancers():
    query = request.args.get('q', '').strip()
    db = get_db()
    users = db.execute(
        "SELECT id, username FROM users WHERE (role = 'tecnico' OR role = 'autonomo') AND username LIKE ? ORDER BY username LIMIT 10",
        (f'%{query}%',)
    ).fetchall()
    return jsonify([dict(user) for user in users])
