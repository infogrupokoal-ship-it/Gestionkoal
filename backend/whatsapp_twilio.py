import os
from twilio.rest import Client
from flask import Blueprint, request, abort, current_app
from twilio.request_validator import RequestValidator
from datetime import datetime
import hashlib

from backend.db import get_db

bp = Blueprint("twilio_wa", __name__)

def send_whatsapp(to_e164: str, text: str):
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    wa_from = os.getenv("TWILIO_WA_FROM")  # e.g., 'whatsapp:+14155238886'

    if not all([sid, token, wa_from]):
        current_app.logger.error("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_WA_FROM not set. Cannot send WhatsApp message.")
        return None

    try:
        client = Client(sid, token)
        message = client.messages.create(
            from_=wa_from,
            to=f"whatsapp:{to_e164}",   # ejemplo: +34XXXXXXXXX
            body=text
        )
        current_app.logger.info(f"WhatsApp message sent to {to_e164}: {message.sid}")
        return message.sid
    except Exception as e:
        current_app.logger.error(f"Error sending WhatsApp message to {to_e164}: {e}")
        return None

@bp.route("/webhooks/twilio/whatsapp", methods=["POST"])
def twilio_whatsapp_webhook():
    # Validación de seguridad
    validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))
    signature = request.headers.get("X-Twilio-Signature", "")
    url = request.url  # debe coincidir exactamente con el configurado en Twilio
    body = request.form.to_dict()

    if not validator.validate(url, body, signature):
        current_app.logger.warning("Invalid Twilio signature for webhook.")
        abort(403)

    # Ejemplo: leer el mensaje
    from_number = request.form.get("From")        # 'whatsapp:+34...'
    text = request.form.get("Body")               # texto recibido
    message_sid = request.form.get("SmsSid") # or MessageSid for WhatsApp
    message_status = request.form.get("MessageStatus")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    if db:
        try:
            # Save webhook status (without PII in message body)
            db.execute(
                "INSERT INTO whatsapp_message_logs (message_id, status, timestamp, from_number_hash) VALUES (?, ?, ?, ?)",
                (message_sid, message_status, timestamp, hashlib.sha256(from_number.encode()).hexdigest() if from_number else None)
            )
            db.commit()
            current_app.logger.info(f"WhatsApp webhook received: SID={message_sid}, Status={message_status}")
        except Exception as e:
            current_app.logger.error(f"Error saving WhatsApp webhook status: {e}")
            db.rollback()

    # TODO: procesar -> crear aviso, responder, etc.
    return "OK", 200

# Test route (for quick testing, remove in production)
@bp.route("/test/wa")
def test_wa():
    to = request.args.get("to")  # ej: +34XXXXXXXXX (el móvil que uniste al Sandbox)
    if not to:
        return jsonify({"error": "Parameter 'to' is required."}), 400
    
    sid = send_whatsapp(to, "Prueba WhatsApp desde Grupo Koal ✅")
    if sid:
        return jsonify({"ok": True, "sid": sid}), 200
    else:
        return jsonify({"ok": False, "message": "Failed to send WhatsApp message."}), 500
