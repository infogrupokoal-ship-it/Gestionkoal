import functools
import os
import logging

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
from flask_login import login_required
import google.generativeai as genai

from backend.db import get_db

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

def _get_ai_response(user_message, chat_history):
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        return "Error: La clave de la API de Gemini no está configurada. El administrador debe configurarla."

    try:
        genai.configure(api_key=api_key) # Configure API key
        model_name = current_app.config.get("GEMINI_MODEL", "gemini-1.0-pro") # Get normalized model name
        model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
        chat = model.start_chat(history=chat_history)
        api_response = chat.send_message(user_message)
        response_text = api_response.text
    except Exception as e:
        # Log the error for debugging
        print(f"Error communicating with AI: {e}")
        # Provide a more specific error to the user
        response_text = f"Lo siento, ha ocurrido un error al contactar con el servicio de IA: {e}"
    return response_text

@bp.route('/', methods=('GET', 'POST'))
@login_required
def chat_interface():
    if not current_app.config.get("AI_CHAT_ENABLED"):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"error": "AI no disponible: configure GEMINI_API_KEY."}), 503
        else:
            flash("El chat de IA está deshabilitado porque falta la clave de API.", "error")
            return render_template('ai_chat/chat.html', chat_history=[], response_text="IA deshabilitada.")

    chat_history = session.get('ai_chat_history', [])
    response_text = None

    if request.method == 'POST':
        try:
            # The plan's example uses request.get_json, but my form uses request.form
            user_message = request.form.get('message', '').strip()
            if not user_message:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "Mensaje vacío."}), 400
                else:
                    flash('Por favor, introduce un mensaje.', 'warning')
            else:
                # The plan suggests calling genai directly here, but I have _get_ai_response
                # I will keep _get_ai_response for now, as it already has error handling
                response_text = _get_ai_response(user_message, chat_history)
                chat_history.append({'role': 'user', 'parts': [user_message]})
                chat_history.append({'role': 'model', 'parts': [response_text]})
                session['ai_chat_history'] = chat_history
        except Exception:
            current_app.logger.exception("AI chat error in chat_interface")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "Se produjo un error procesando tu mensaje."}), 500
            else:
                flash("Se produjo un error procesando tu mensaje.", "error")

    return render_template('ai_chat/chat.html', chat_history=chat_history, response_text=response_text)

@bp.route('/content', methods=('GET', 'POST'))
@login_required
def chat_content():
    if not current_app.config.get("AI_CHAT_ENABLED"):
        # This is an AJAX endpoint, so always return JSON
        return jsonify({"error": "AI no disponible: configure GEMINI_API_KEY."}), 503

    chat_history = session.get('ai_chat_history', [])
    response_text = None

    if request.method == 'POST':
        try:
            user_message = request.form.get('message', '').strip()
            if not user_message:
                return jsonify({"error": "Mensaje vacío."}), 400
            else:
                response_text = _get_ai_response(user_message, chat_history)
                chat_history.append({'role': 'user', 'parts': [user_message]})
                chat_history.append({'role': 'model', 'parts': [response_text]})
                session['ai_chat_history'] = chat_history
        except Exception:
            current_app.logger.exception("AI chat error in chat_content")
            return jsonify({"error": "Se produjo un error procesando tu mensaje."}), 500
    
    return render_template('ai_chat/chat.html', chat_history=chat_history, response_text=response_text)


@bp.route('/clear_history', methods=('POST',))
@login_required
def clear_history():
    session.pop('ai_chat_history', None)
    flash('Historial del chat limpiado.', 'info')
    # If coming from AJAX, return the empty chat content
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('ai_chat/chat.html', chat_history=[], response_text=None)
    return redirect(url_for('ai_chat.chat_interface'))