from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, jsonify
from flask_login import login_required

# Import the new centralized client function
from backend.gemini_client import generate_chat_response

bp = Blueprint('ai_chat', __name__, url_prefix='/ai_chat')

system_instruction = """
Eres un asistente de IA para la aplicación de gestión de servicios de Grupo Koal.
Tu objetivo es ayudar a los usuarios a:
1.  **Entender y utilizar la aplicación:** Responde preguntas sobre cómo navegar, usar funciones, etc.
2.  **Informar sobre los servicios y materiales de Grupo Koal:** Proporciona información general sobre los tipos de servicios que ofrece Grupo Koal (mantenimiento, reparaciones, instalaciones, etc.) y los materiales que utilizan.
3.  **Guiar en procesos de ventas:** Si un usuario pregunta sobre precios, presupuestos o cómo contratar un servicio, dirígele sobre los pasos a seguir en la aplicación o cómo contactar con el equipo de ventas.
4.  **Reportar errores o sugerencias:** Si un usuario menciona un error o tiene una sugerencia, dirígele al formulario de "Reportar Error" disponible en la barra de navegación.

Sé amable, conciso y siempre enfocado en la información relevante para Grupo Koal y el uso de la aplicación.
"""

def handle_chat_submission():
    """Helper function to process chat form submissions for both routes."""
    chat_history = session.get('ai_chat_history', [])
    user_message = request.form.get('message', '').strip()

    if not user_message:
        return {"error": "Mensaje vacío."}, 400

    try:
        # Use the new centralized client
        response_text = generate_chat_response(chat_history, user_message, system_instruction)
        
        chat_history.append({'role': 'user', 'parts': [user_message]})
        chat_history.append({'role': 'model', 'parts': [response_text]})
        session['ai_chat_history'] = chat_history
        return None, None # Success
    except Exception as e:
        current_app.logger.exception("AI chat submission error")
        return {"error": f"Se produjo un error procesando tu mensaje: {e}"}, 500

@bp.route('/', methods=('GET', 'POST'))
@login_required
def chat_interface():
    if not current_app.config.get("AI_CHAT_ENABLED"):
        flash("El chat de IA está deshabilitado porque falta la clave de API.", "error")
        return render_template('ai_chat/chat.html', chat_history=[], response_text="IA deshabilitada.")

    if request.method == 'POST':
        error_response, status_code = handle_chat_submission()
        if error_response:
            flash(error_response.get('error', 'Ocurrió un error.'), 'error')

    chat_history = session.get('ai_chat_history', [])
    return render_template('ai_chat/chat.html', chat_history=chat_history)

@bp.route('/content', methods=('GET', 'POST'))
@login_required
def chat_content():
    if not current_app.config.get("AI_CHAT_ENABLED"):
        return jsonify({"error": "AI no disponible: configure GEMINI_API_KEY."}), 503

    if request.method == 'POST':
        error_response, status_code = handle_chat_submission()
        if error_response:
            return jsonify(error_response), status_code
    
    chat_history = session.get('ai_chat_history', [])
    return render_template('ai_chat/chat.html', chat_history=chat_history)

@bp.route('/clear_history', methods=('POST',))
@login_required
def clear_history():
    session.pop('ai_chat_history', None)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('ai_chat/chat.html', chat_history=[])
    flash('Historial del chat limpiado.', 'info')
    return redirect(url_for('ai_chat.chat_interface'))