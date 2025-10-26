# backend/ai_endpoints.py
from flask import Blueprint, request, jsonify
from flask_login import login_required
from sqlalchemy import text

from backend.extensions import db
from backend.assignment import suggest_assignee
from backend.llm import ask_gemini_json
from backend.whatsapp import WhatsAppClient


bp = Blueprint('ai_endpoints', __name__, url_prefix='/ai')


@bp.route('/tickets/<int:ticket_id>/reassign', methods=['POST'])
@login_required
def reassign_ticket(ticket_id):
    ticket = db.session.execute(text("SELECT * FROM tickets WHERE id = :id"), {"id": ticket_id}).fetchone()
    client = None
    if ticket:
        client = db.session.execute(text("SELECT * FROM clientes WHERE id = :id"), {"id": ticket.cliente_id}).fetchone()
    if not ticket or not client:
        return jsonify({"ok": False, "error": "Ticket or client not found"}), 404

    assignee = suggest_assignee(db.session, ticket.tipo, ticket.prioridad, client)
    if assignee:
        db.session.execute(text("UPDATE tickets SET asignado_a = :uid WHERE id = :id"), {"uid": assignee['id'], "id": ticket_id})
        db.session.commit()
        return jsonify({"ok": True, "assigned_to": assignee['username']})
    return jsonify({"ok": False, "error": "No suitable assignee found"})


@bp.route('/tickets/<int:ticket_id>/suggest_reply', methods=['POST'])
@login_required
def suggest_ticket_reply(ticket_id):
    ticket = db.session.execute(text("SELECT * FROM tickets WHERE id = :id"), {"id": ticket_id}).fetchone()
    if not ticket:
        return jsonify({"ok": False, "error": "Ticket not found"}), 404

    context = f"Ticket ID: {ticket.id}, Título: {ticket.titulo}, Descripción: {ticket.descripcion}, Estado: {ticket.estado}"
    reply_suggestion = ask_gemini_json("suggest_reply", {"context": context})
    return jsonify({"ok": True, "reply": reply_suggestion.get("reply_text")})


@bp.route('/tickets/<int:ticket_id>/send_reply', methods=['POST'])
@login_required
def send_ticket_reply(ticket_id):
    ticket = db.session.execute(text("SELECT * FROM tickets WHERE id = :id"), {"id": ticket_id}).fetchone()
    client = None
    if ticket:
        client = db.session.execute(text("SELECT * FROM clientes WHERE id = :id"), {"id": ticket.cliente_id}).fetchone()
    if not ticket or not client:
        return jsonify({"ok": False, "error": "Ticket or client not found"}), 404

    message = (request.json or {}).get('message')
    if not message:
        return jsonify({"ok": False, "error": "Message is required"}), 400

    phone = client.telefono
    if not phone:
        return jsonify({"ok": False, "error": "Client has no phone number"}), 400

    response = WhatsAppClient().send_text(phone, message)
    return jsonify(response)

