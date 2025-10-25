from flask import Blueprint, jsonify, request

from backend.db_utils import get_db

bp = Blueprint('autocomplete', __name__, url_prefix='/autocomplete')

# Autocompletion endpoint for clients
@bp.route('/clients')
def autocomplete_clients():
    """Provides autocompletion suggestions for client names based on a query string."""
    query = request.args.get('q', '').strip()
    db = get_db()
    if db is None:
        return jsonify({"error": "Database connection error"}), 500
    clients = db.execute(
        'SELECT id, nombre FROM clientes WHERE nombre LIKE ? ORDER BY nombre LIMIT 10',
        (f'%{query}%',)
    ).fetchall()
    return jsonify([dict(client) for client in clients])

# Autocompletion endpoint for materials
@bp.route('/materials')
def autocomplete_materials():
    """Provides autocompletion suggestions for material names and SKUs based on a query string."""
    query = request.args.get('q', '').strip()
    db = get_db()
    if db is None:
        return jsonify({"error": "Database connection error"}), 500
    materials = db.execute(
        'SELECT id, nombre, sku FROM materiales WHERE nombre LIKE ? OR sku LIKE ? ORDER BY nombre LIMIT 10',
        (f'%{query}%', f'%{query}%')
    ).fetchall()
    return jsonify([dict(material) for material in materials])

# Autocompletion endpoint for services
@bp.route('/services')
def autocomplete_services():
    """Provides autocompletion suggestions for service names and descriptions based on a query string."""
    query = request.args.get('q', '').strip()
    db = get_db()
    if db is None:
        return jsonify({"error": "Database connection error"}), 500
    services = db.execute(
        'SELECT id, name, description FROM services WHERE name LIKE ? OR description LIKE ? ORDER BY name LIMIT 10',
        (f'%{query}%', f'%{query}%')
    ).fetchall()
    return jsonify([dict(service) for service in services])

# Autocompletion endpoint for technicians and freelancers
@bp.route('/technicians_freelancers')
def autocomplete_technicians_freelancers():
    """Provides autocompletion suggestions for technician and freelancer usernames based on a query string."""
    query = request.args.get('q', '').strip()
    db = get_db()
    if db is None:
        return jsonify({"error": "Database connection error"}), 500
    users = db.execute(
        "SELECT id, username FROM users WHERE (role = 'tecnico' OR role = 'autonomo') AND username LIKE ? ORDER BY username LIMIT 10",
        (f'%{query}%',)
    ).fetchall()
    return jsonify([dict(user) for user in users])
