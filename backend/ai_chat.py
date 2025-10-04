# backend/ai_chat.py
from flask import Blueprint, current_app, request, session, jsonify, render_template, redirect, url_for
from flask_login import login_required
import os, re
import google.generativeai as genai
from backend.db import get_db # Import get_db

bp = Blueprint('ai_chat', __name__, url_prefix='/ai_chat')

SYSTEM_INSTRUCTION = (
    "Eres un asistente de IA para la aplicación Gestión Koal. "
    "Ayuda con uso de la app, servicios/materiales y procesos de ventas. "
    "Ten en cuenta las medidas y estándares de España al proporcionar datos o sugerencias. "
    "Sé amable y conciso."
)

def _sanitize_model(name: str) -> str:
    n = name.strip()
    # Si ya es un nombre completo con prefijo models/, no lo alteres
    if n.startswith("models/"):
        return n
    # Solo sanea alias cortos (sin "models/")
    return re.sub(r'-(?:\d{3}|latest)$', '', n.lower())

def _coerce_history(raw):
    """Convierte el historial de sesión a [{role, parts:[texto]}], y limita a 20."""
    out = []
    for m in (raw or []):
        try:
            role = m.get("role")
            parts = m.get("parts", [])
            if isinstance(parts, list) and parts:
                text = str(parts[0])
            else:
                text = str(parts) if parts is not None else ""
            if role in ("user", "model"):
                out.append({"role": role, "parts": [text]})
        except Exception:
            continue
    return out[-20:]

def _get_ai_response(user_message, chat_history):
    api_key = current_app.config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: La clave de API de Gemini no está configurada."

    # Usa el modelo de la app o el estable por defecto
    configured = current_app.config.get("GEMINI_MODEL") or "models/gemini-flash-latest"
    model_name = configured  # ya normalizado en create_app
    hist = _coerce_history(chat_history)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name, system_instruction=SYSTEM_INSTRUCTION)
        chat = model.start_chat(history=hist)
        resp = chat.send_message(user_message)
        return resp.text
    except Exception as e:
        current_app.logger.warning("Primario %s falló: %s. Probando fallback models/gemini-flash-latest", model_name, e)
        try:
            model = genai.GenerativeModel("models/gemini-flash-latest", system_instruction=SYSTEM_INSTRUCTION)
            chat = model.start_chat(history=hist)
            resp = chat.send_message(user_message)
            return resp.text
        except Exception as e2:
            current_app.logger.exception("Fallback también falló: %s", e2)
            return "Lo siento, ha ocurrido un error al contactar con el servicio de IA."

@bp.get("/content")
def content():
    # Renderiza la vista del chat (prueba ambas rutas por si el template está en /templates/ai_chat.html)
    return current_app.jinja_env.get_or_select_template(["ai_chat/chat.html", "ai_chat.html"]).render(
        chat_history=session.get('ai_chat_history', []),
        AI_CHAT_ENABLED=current_app.config.get("AI_CHAT_ENABLED", False)
    )

@bp.post("/")
def submit():
    try:
        chat_history = session.get('ai_chat_history', [])
        data = request.get_json(silent=True) or {}
        user_message = data.get('message', '').strip()
        job_id = data.get('job_id', type=int)
        current_url = data.get('current_url', '')

        if not user_message:
            return jsonify({"error": "Mensaje vacío."}), 400

        enriched_user_message = user_message

        if job_id:
            db = get_db()
            job_details = db.execute(
                '''SELECT t.titulo, t.descripcion, t.estado, c.nombre as client_name, u.username as assigned_freelancer
                   FROM tickets t
                   LEFT JOIN clientes c ON t.cliente_id = c.id
                   LEFT JOIN users u ON t.asignado_a = u.id
                   WHERE t.id = ?''',
                (job_id,)
            ).fetchone()
            if job_details:
                enriched_user_message = (
                    f"El usuario está en la página del trabajo ID {job_id}. "
                    f"Título: {job_details['titulo']}, Descripción: {job_details['descripcion']}, "
                    f"Estado: {job_details['estado']}, Cliente: {job_details['client_name']}, "
                    f"Autónomo Asignado: {job_details['assigned_freelancer'] or 'N/A'}. "
                    f"Pregunta del usuario: {user_message}"
                )
            else:
                enriched_user_message = (
                    f"El usuario está en la página del trabajo ID {job_id} (no encontrado en la base de datos). "
                    f"Pregunta del usuario: {user_message}"
                )
        elif current_url:
            enriched_user_message = (
                f"El usuario está en la página: {current_url}. "
                f"Pregunta del usuario: {user_message}"
            )

        reply = _get_ai_response(enriched_user_message, chat_history)

        chat_history.append({'role': 'user', 'parts': [user_message]})
        chat_history.append({'role': 'model', 'parts': [reply]})
        session['ai_chat_history'] = chat_history

        return jsonify({"ok": True, "reply": reply}), 200
    except Exception as e:
        current_app.logger.exception("AI chat submission error: %s", e)
        return jsonify({"error": "internal server error"}), 500

@bp.post("/clear_history")
def clear_history():
    session['ai_chat_history'] = []
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('ai_chat/chat.html', chat_history=[])
    from flask import redirect, url_for, flash
    flash('Historial del chat limpiado.', 'info')
    return redirect(url_for('ai_chat.content'))