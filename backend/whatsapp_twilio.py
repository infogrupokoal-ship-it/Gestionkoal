import hashlib
import os
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint("twilio_wa", __name__, url_prefix="/whatsapp")

def send_whatsapp(to_e164: str, text: str):
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    wa_from = os.getenv("TWILIO_WA_FROM")  # e.g., 'whatsapp:+14155238886'

    if not all([sid, token, wa_from]):
        current_app.logger.error("TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, or TWILIO_WA_FROM not set. Cannot send WhatsApp message.",
                                   extra={'event': 'whatsapp_send_failed', 'reason': 'missing_credentials'})
        return None

    try:
        client = Client(sid, token)
        message = client.messages.create(
            from_=wa_from,
            to=f"whatsapp:{to_e164}",   # ejemplo: +34XXXXXXXXX
            body=text
        )
        current_app.logger.info(f"WhatsApp message sent. SID: {message.sid}",
                                extra={'event': 'whatsapp_sent', 'message_sid': message.sid, 'to_number_hash': hashlib.sha256(to_e164.encode()).hexdigest()})
        return message.sid
    except Exception as e:
        current_app.logger.error(f"Error sending WhatsApp message. Error: {e}",
                                   extra={'event': 'whatsapp_send_failed', 'error': str(e), 'to_number_hash': hashlib.sha256(to_e164.encode()).hexdigest()})
        return None

@bp.route("/webhooks/twilio/whatsapp", methods=["POST"])
def twilio_whatsapp_webhook():
    # Validación de seguridad
    validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))
    signature = request.headers.get("X-Twilio-Signature", "")
    url = request.url  # debe coincidir exactamente con el configurado en Twilio
    body = request.form.to_dict()

    if not validator.validate(url, body, signature):
        current_app.logger.warning("Invalid Twilio signature for webhook.", extra={'event': 'whatsapp_webhook_invalid_signature'})
        abort(403)

    # Ejemplo: leer el mensaje
    from_number = request.form.get("From")        # 'whatsapp:+34...'
    # text = request.form.get("Body")               # texto recibido - Removed unused variable
    message_sid = request.form.get("SmsSid") # or MessageSid for WhatsApp
    message_status = request.form.get("MessageStatus")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    db = get_db()
    if db is None:
        current_app.logger.error("Database connection error in Twilio WhatsApp webhook.")
        return "Database connection error", 500
    if db:
        try:
            # Save webhook status (without PII in message body)
            db.execute(
                "INSERT INTO whatsapp_message_logs (message_id, status, timestamp, from_number_hash) VALUES (?, ?, ?, ?)",
                (message_sid, message_status, timestamp, hashlib.sha256(from_number.encode()).hexdigest() if from_number else None)
            )
            db.commit()
            current_app.logger.info(f"WhatsApp webhook received: SID={message_sid}, Status={message_status}",
                                    extra={'event': 'whatsapp_webhook_received', 'message_sid': message_sid, 'status': message_status, 'from_number_hash': hashlib.sha256(from_number.encode()).hexdigest() if from_number else None})
        except Exception as e:
            current_app.logger.error(f"Error saving WhatsApp webhook status: {e}",
                                     extra={'event': 'whatsapp_webhook_save_error', 'error': str(e), 'message_sid': message_sid})
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

@bp.route("/logs")
@login_required
def list_whatsapp_logs():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    logs = db.execute(
        "SELECT id, message_id, status, timestamp, from_number_hash FROM whatsapp_message_logs ORDER BY timestamp DESC"
    ).fetchall()
    return render_template("whatsapp_message_logs/list.html", logs=logs)