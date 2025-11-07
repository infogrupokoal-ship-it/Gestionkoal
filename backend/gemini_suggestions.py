from flask import Blueprint, current_app, jsonify, request

from backend.db_utils import insertar_material, insertar_servicio  # Added
from backend.sugerencias import sugerir_materiales_servicios

gemini_bp = Blueprint("gemini", __name__, url_prefix="/gemini")

@gemini_bp.route("/sugerencias", methods=["POST"])
def sugerencias():
    data = request.get_json()
    descripcion = data.get("descripcion", "")

    if not descripcion.strip():
        return jsonify({"error": "La descripción es obligatoria"}), 400

    try:
        resultado = sugerir_materiales_servicios(descripcion)

        if resultado is None:
            return jsonify({"error": "No se pudo obtener sugerencias de Gemini"}), 500

        materiales = resultado.get("materiales", [])
        servicios = resultado.get("servicios", [])

        for m in materiales:
            insertar_material(m)

        for s in servicios:
            insertar_servicio(s)

        return jsonify({"estado": "ok", "materiales_insertados": len(materiales), "servicios_insertados": len(servicios)}), 201
    except Exception as e:
        current_app.logger.error(f"Error en /gemini/sugerencias: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor al procesar la sugerencia"}), 500
