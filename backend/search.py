from flask import Blueprint, jsonify, request

from backend.db_utils import get_db_connection

search_bp = Blueprint("search", __name__)

@search_bp.route("/api/global_search")
def global_search():
    query = request.args.get("q", "").lower()
    results = {"materiales": [], "servicios": [], "trabajos": []}

    if not query:
        return jsonify(results)

    conn = get_db_connection()

    # Buscar en Materiales
    materiales = conn.execute("SELECT id, nombre, descripcion FROM materiales WHERE LOWER(nombre) LIKE ? OR LOWER(descripcion) LIKE ? LIMIT 5", (f"%{query}%", f"%{query}%")).fetchall()
    results["materiales"] = [dict(m) for m in materiales]

    # Buscar en Servicios
    servicios = conn.execute("SELECT id, nombre, descripcion FROM servicios WHERE LOWER(nombre) LIKE ? OR LOWER(descripcion) LIKE ? LIMIT 5", (f"%{query}%", f"%{query}%")).fetchall()
    results["servicios"] = [dict(s) for s in servicios]

    # Buscar en Trabajos (Tickets)
    trabajos = conn.execute("SELECT id, titulo, descripcion FROM tickets WHERE LOWER(titulo) LIKE ? OR LOWER(descripcion) LIKE ? LIMIT 5", (f"%{query}%", f"%{query}%")).fetchall()
    results["trabajos"] = [dict(t) for t in trabajos]

    conn.close()
    return jsonify(results)
