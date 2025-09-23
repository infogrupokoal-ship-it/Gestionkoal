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

@bp.route('/', methods=('GET', 'POST'))
@login_required
def chat_interface():
    chat_history = session.get('ai_chat_history', [])
    response_text = None

    if request.method == 'POST':
        user_message = request.form['message']
        if not user_message:
            flash('Please enter a message.', 'warning')
        else:
            try:
                # Initialize the model
                model = genai.GenerativeModel('gemini-pro')
                
                # Start a chat session with the current history
                chat = model.start_chat(history=chat_history)
                
                # Send the user's message and get response
                api_response = chat.send_message(user_message)
                response_text = api_response.text

                # Update chat history in session
                chat_history.append({'role': 'user', 'parts': [user_message]})
                chat_history.append({'role': 'model', 'parts': [response_text]})
                session['ai_chat_history'] = chat_history

            except Exception as e:
                flash(f'Error communicating with AI: {e}', 'error')
                response_text = "Lo siento, no pude procesar tu solicitud en este momento."

    return render_template('ai_chat/chat.html', chat_history=chat_history, response_text=response_text)

@bp.route('/clear_history', methods=('POST',))
@login_required
def clear_history():
    session.pop('ai_chat_history', None)
    flash('Chat history cleared.', 'info')
    return redirect(url_for('ai_chat.chat_interface'))
