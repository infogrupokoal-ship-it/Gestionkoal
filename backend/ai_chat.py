import functools
import os

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from flask_login import login_required
import google.generativeai as genai

from backend.db import get_db

bp = Blueprint('ai_chat', __name__, url_prefix='/ai_chat')

# Configure Gemini API
# Ensure GEMINI_API_KEY is set in your environment variables
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

system_instruction = """
Eres un asistente de IA para la aplicación de gestión de servicios de Grupo Koal.
Tu objetivo es ayudar a los usuarios a:
1.  **Entender y utilizar la aplicación:** Responde preguntas sobre cómo navegar, usar funciones, etc.
2.  **Informar sobre los servicios y materiales de Grupo Koal:** Proporciona información general sobre los tipos de servicios que ofrece Grupo Koal (mantenimiento, reparaciones, instalaciones, etc.) y los materiales que utilizan.
3.  **Guiar en procesos de ventas:** Si un usuario pregunta sobre precios, presupuestos o cómo contratar un servicio, guíale sobre los pasos a seguir en la aplicación o cómo contactar con el equipo de ventas.
4.  **Reportar errores o sugerencias:** Si un usuario menciona un error o tiene una sugerencia, dirígele al formulario de "Reportar Error" disponible en la barra de navegación.

Sé amable, conciso y siempre enfocado en la información relevante para Grupo Koal y el uso de la aplicación.
"""

def _get_ai_response(user_message, chat_history):
    response_text = None
    try:
        model = genai.GenerativeModel('gemini-pro', system_instruction=system_instruction)
        chat = model.start_chat(history=chat_history)
        api_response = chat.send_message(user_message)
        response_text = api_response.text
    except Exception as e:
        # Log the error for debugging
        print(f"Error communicating with AI: {e}")
        response_text = "Lo siento, no pude procesar tu solicitud en este momento. Asegúrate de que tu GEMINI_API_KEY esté configurada correctamente."
    return response_text

@bp.route('/', methods=('GET', 'POST'))
@login_required
def chat_interface():
    chat_history = session.get('ai_chat_history', [])
    response_text = None

    if request.method == 'POST':
        user_message = request.form['message']
        if not user_message:
            flash('Por favor, introduce un mensaje.', 'warning')
        else:
            response_text = _get_ai_response(user_message, chat_history)
            chat_history.append({'role': 'user', 'parts': [user_message]})
            chat_history.append({'role': 'model', 'parts': [response_text]})
            session['ai_chat_history'] = chat_history

    return render_template('ai_chat/chat.html', chat_history=chat_history, response_text=response_text)

@bp.route('/content', methods=('GET', 'POST'))
@login_required
def chat_content():
    chat_history = session.get('ai_chat_history', [])
    response_text = None

    if request.method == 'POST':
        user_message = request.form['message']
        if not user_message:
            # This case should be handled by client-side validation, but good to have
            response_text = "Por favor, introduce un mensaje."
        else:
            response_text = _get_ai_response(user_message, chat_history)
            chat_history.append({'role': 'user', 'parts': [user_message]})
            chat_history.append({'role': 'model', 'parts': [response_text]})
            session['ai_chat_history'] = chat_history
    
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