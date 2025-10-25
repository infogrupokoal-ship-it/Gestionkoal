# backend/whatsapp_webhook.py
import os
from flask import Blueprint, request, jsonify, current_app
from backend.whatsapp import save_whatsapp_log, WhatsAppClient

bp = Blueprint("whatsapp_webhook", __name__, url_prefix="/webhooks/whatsapp")

@bp.route("/", methods=["GET"])
def verify():
    # Meta verification
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == verify_token:
        return challenge, 200
    return "forbidden", 403

@bp.route("/", methods=["POST"])
def receive():
    data = request.get_json(silent=True) or {}
    # Guarda todo el payload inbound
    try:
        phone, text = None, None

        # Meta Cloud typical structure
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", []) or []
        if messages:
            msg = messages[0]
            phone = msg.get("from")
            if msg.get("type") == "text":
                text = (msg.get("text") or {}).get("body")

        save_whatsapp_log("inbound", phone, text, os.getenv("WHATSAPP_PROVIDER","meta"), "received", None, data)

        # (Opcional) auto-respuesta en DRY-RUN para ver ida y vuelta:
        if os.getenv("WHATSAPP_DRY_RUN", "0") == "1" and phone:
            client = WhatsAppClient()
            client.send_text(phone, "¡Recibido! (modo demo)")

        return jsonify({"ok": True}), 200
    except Exception as e:
        current_app.logger.exception("Error processing WA webhook")
        save_whatsapp_log("inbound", None, None, os.getenv("WHATSAPP_PROVIDER","meta"), "error", str(e), data)
        return jsonify({"ok": False}), 500
