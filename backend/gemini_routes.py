from flask import Blueprint, render_template, request, jsonify, current_app
from backend.sugerencias import sugerir_materiales_servicios
from backend.db_utils import insertar_material, insertar_servicio

gemini_ui_bp = Blueprint("gemini_ui", __name__, url_prefix="/gemini_ui")

@gemini_ui_bp.route("/probar", methods=["GET", "POST"])
def probar_gemini():
    sugerencias = None
    error = None

    if request.method == "POST":
        descripcion = request.form.get("descripcion", "").strip()
        if not descripcion:
            error = "Por favor ingresa una descripción."
        else:
            try:
                resultado = sugerir_materiales_servicios(descripcion)
                if resultado:
                    sugerencias = resultado
                    for m in resultado.get("materiales", []):
                        insertar_material(m)
                    for s in resultado.get("servicios", []):
                        insertar_servicio(s)
                else:
                    error = "Gemini no devolvió sugerencias válidas."
            except Exception as e:
                current_app.logger.error(f"Error al obtener sugerencias de Gemini: {e}", exc_info=True)
                error = f"Error interno al obtener sugerencias: {e}"

    return render_template("probar_gemini.html", sugerencias=sugerencias, error=error)
