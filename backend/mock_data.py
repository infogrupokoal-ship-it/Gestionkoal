import json
import os

from flask import Blueprint, current_app, jsonify, render_template, request

mock_data_bp = Blueprint("mock_data", __name__, url_prefix="/mock_data")

@mock_data_bp.route("/messages")
def show_mock_messages():
    all_messages = []
    error_messages = []

    # Cargar mensajes válidos
    try:
        with open(os.path.join(current_app.root_path, 'all_mock_messages.json'), encoding='utf-8') as f:
            all_messages = json.load(f)
    except FileNotFoundError:
        current_app.logger.warning("all_mock_messages.json no encontrado.")
    except json.JSONDecodeError:
        current_app.logger.error("Error al decodificar all_mock_messages.json.")

    # Cargar mensajes con errores
    try:
        with open(os.path.join(current_app.root_path, 'mock_error_messages.json'), encoding='utf-8') as f:
            error_messages = json.load(f)
    except FileNotFoundError:
        current_app.logger.warning("mock_error_messages.json no encontrado.")
    except json.JSONDecodeError:
        current_app.logger.error("Error al decodificar mock_error_messages.json.")

    # Combinar y añadir un indicador de si tiene errores
    for msg in all_messages:
        msg["has_errors"] = False
    for msg in error_messages:
        msg["has_errors"] = True

    all_combined_messages = all_messages + error_messages

    # Filtrado
    filter_type = request.args.get("type")
    filter_priority = request.args.get("priority")
    filter_errors = request.args.get("errors")

    filtered_messages = []
    for msg in all_combined_messages:
        match = True
        if filter_type and msg.get("tipo") != filter_type:
            match = False
        if filter_priority and msg.get("prioridad") != filter_priority:
            match = False
        if filter_errors == "true" and not msg["has_errors"]:
            match = False
        if filter_errors == "false" and msg["has_errors"]:
            match = False

        if match:
            filtered_messages.append(msg)

    return render_template("mock_data/messages.html", messages=filtered_messages,
                           filter_type=filter_type, filter_priority=filter_priority,
                           filter_errors=filter_errors)
@mock_data_bp.route("/error_messages")
def show_mock_error_messages():
    error_messages = []
    try:
        with open(os.path.join(current_app.root_path, 'mock_error_messages.json'), encoding='utf-8') as f:
            error_messages = json.load(f)
    except FileNotFoundError:
        current_app.logger.warning("mock_error_messages.json no encontrado.")
    except json.JSONDecodeError:
        current_app.logger.error("Error al decodificar mock_error_messages.json.")

    # Aquí integramos la lógica de validación del script validar_mensajes.py
    # para mostrar los errores específicos en la vista.
    from validar_mensajes import validate_message  # Importar la función de validación

    messages_with_validation = []
    for i, msg in enumerate(error_messages):
        errors = validate_message(msg, i) # Usar la función de validación
        messages_with_validation.append({
            "original_message": msg,
            "validation_errors": errors,
            "is_valid": not errors
        })

    return render_template("mock_data/error_messages.html", messages=messages_with_validation)

@mock_data_bp.route("/api/mensajes", methods=["GET"])
def api_get_mensajes_mock():
    ruta = os.path.join(current_app.root_path, "all_mock_messages.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    return jsonify(data)

@mock_data_bp.route("/api/mensajes_errores", methods=["GET"])
def api_get_mensajes_con_errores():
    ruta = os.path.join(current_app.root_path, "mock_error_messages.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    return jsonify(data)

@mock_data_bp.route("/api/mensajes", methods=["POST"])
def api_insert_mensaje():
    nuevo = request.get_json()
    if not nuevo:
        return jsonify({"error": "Datos vacíos o mal formateados"}), 400

    ruta = os.path.join(current_app.root_path, "all_mock_messages.json")
    try:
        with open(ruta, "r+", encoding="utf-8") as f:
            datos = json.load(f)
            datos.append(nuevo)
            f.seek(0)
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.truncate()
    except FileNotFoundError:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump([nuevo], f, ensure_ascii=False, indent=2)
    except Exception as e:
        current_app.logger.error(f"Error al insertar mensaje via API: {e}")
        return jsonify({"error": "Error interno al guardar el mensaje"}), 500

    return jsonify({"estado": "ok", "mensaje": "Insertado correctamente"}), 201

