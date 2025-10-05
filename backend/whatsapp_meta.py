import hashlib
import hmac
import json
import os
import re

from flask import Blueprint, current_app, jsonify, request

from .db import _execute_sql, get_db  # Import _execute_sql
from .wa_client import send_whatsapp_text

whatsapp_meta_bp = Blueprint('whatsapp_meta', __name__, url_prefix='/webhooks/whatsapp')



def save_whatsapp_log(job_id, material_id, provider_id, direction, from_number, to_number, message_body, whatsapp_message_id=None, status=None, error_info=None):
    db = get_db()
    if db is None:
        current_app.logger.error("Database connection error in save_whatsapp_log.")
        return
    cursor = db.cursor()
    _execute_sql(
        """
        INSERT INTO whatsapp_message_logs (job_id, material_id, provider_id, direction, from_number, to_number, message_body, whatsapp_message_id, status, error_info)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (job_id, material_id, provider_id, direction, from_number, to_number, message_body, whatsapp_message_id, status, error_info),
        cursor=cursor,
        commit=True
    )
    current_app.logger.info(f"WhatsApp log saved: {direction} from {from_number} to {to_number} - {message_body}")

def handle_incoming_message(from_number, message_body, whatsapp_message_id):
    current_app.logger.info(f"Incoming WhatsApp message from {from_number}: {message_body}")

    db = get_db()
    if db is None:
        current_app.logger.error("Database connection error in handle_incoming_message.")
        return
    cursor = db.cursor()

    provider_id = None
    job_id = None
    material_id = None
    quote_amount = None
    quote_currency = 'EUR' # Default currency

    # 1. Identify the provider based on from_number
    # Assuming provider phone numbers are stored in a 'phone_number' column in the 'providers' table
    # We need to normalize the phone number format for comparison (e.g., remove '+')
    normalized_from_number = from_number.replace('+', '') # Example normalization

    provider_row = _execute_sql(
        "SELECT id FROM providers WHERE whatsapp_number = ? OR phone_number = ?",
        (normalized_from_number, normalized_from_number),
        cursor=cursor,
        fetchone=True
    )
    if provider_row:
        provider_id = provider_row['id']
        current_app.logger.info(f"Identified provider_id: {provider_id} from number {from_number}")
    else:
        current_app.logger.warning(f"Could not identify provider from number: {from_number}")
        # Save log without provider_id, job_id, material_id
        save_whatsapp_log(
            job_id=None, material_id=None, provider_id=None,
            direction='inbound', from_number=from_number,
            to_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
            message_body=message_body, whatsapp_message_id=whatsapp_message_id,
            status='received', error_info='Provider not identified'
        )
        return # Cannot process further without a provider

    # 2. Find the most recent 'pending' quote request sent to this provider
    # Look for an outbound message to this provider that is part of a pending quote request
    # This is a bit tricky. We need to link whatsapp_message_logs to provider_quotes.
    # A simpler approach for now: find the most recent outbound message to this provider
    # that has an associated job_id and material_id, and then check if there's a pending quote.

    # Find the most recent outbound message to this provider
    last_outbound_log = _execute_sql(
        """
        SELECT job_id, material_id
        FROM whatsapp_message_logs
        WHERE provider_id = ? AND direction = 'outbound'
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (provider_id,),
        cursor=cursor,
        fetchone=True
    )

    if last_outbound_log and last_outbound_log['job_id'] and last_outbound_log['material_id']:
        job_id = last_outbound_log['job_id']
        material_id = last_outbound_log['material_id']

        # Check if there's a pending quote for this job, material, and provider
        pending_quote = _execute_sql(
            """
            SELECT id FROM provider_quotes
            WHERE job_id = ? AND material_id = ? AND provider_id = ? AND status = 'pending'
            ORDER BY id DESC
            LIMIT 1
            """,
            (job_id, material_id, provider_id),
            cursor=cursor,
            fetchone=True
        )
        if not pending_quote:
            current_app.logger.warning(f"No pending quote found for provider {provider_id}, job {job_id}, material {material_id}")
            # Log and return, as we can't link this response to a specific pending request
            save_whatsapp_log(
                job_id=job_id, material_id=material_id, provider_id=provider_id,
                direction='inbound', from_number=from_number,
                to_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
                message_body=message_body, whatsapp_message_id=whatsapp_message_id,
                status='received', error_info='No pending quote found'
            )
            return
    else:
        current_app.logger.warning(f"No recent outbound message with job/material ID found for provider {provider_id}")
        # Log and return
        save_whatsapp_log(
            job_id=None, material_id=None, provider_id=provider_id,
            direction='inbound', from_number=from_number,
            to_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
            message_body=message_body, whatsapp_message_id=whatsapp_message_id,
            status='received', error_info='No recent outbound message with job/material ID'
        )
        return

    # 3. Parse the message_body for a quote amount
    # Enhanced regex to look for numbers near keywords like 'precio', 'costo', 'cotizacion', '€', 'euros'
    # It tries to capture a number (integer or decimal with comma/dot)
    # and is more flexible about surrounding text.
    match = re.search(
        r'(?:precio|costo|cotizaci[oó]n|valor|total|es)\s*[:=]?\s*(\d+[\.,]?\d*)\s*(?:€|eur|euros)?'
        r'|(\d+[\.,]?\d*)\s*(?:€|eur|euros)?',
        message_body, re.IGNORECASE
    )
    if match:
        # Prioritize the number found after a keyword, otherwise take the standalone number
        quote_amount_str = match.group(1) if match.group(1) else match.group(2)
        if quote_amount_str:
            quote_amount_str = quote_amount_str.replace(',', '.') # Replace comma decimal with dot
            try:
                quote_amount = float(quote_amount_str)
                current_app.logger.info(f"Parsed quote amount: {quote_amount}")
            except ValueError:
                current_app.logger.warning(f"Could not convert '{quote_amount_str}' to float.")
        else:
            current_app.logger.warning(f"Could not extract quote amount from message: {message_body}")
    else:
        current_app.logger.warning(f"Could not parse quote amount from message: {message_body}")

    # 4. Update the provider_quotes table
    if job_id and material_id and provider_id and quote_amount is not None:
        _execute_sql(
            """
            UPDATE provider_quotes
            SET quote_amount = ?, quote_currency = ?, quote_date = CURRENT_TIMESTAMP,
                response_message = ?, status = 'received', whatsapp_message_id = ?
            WHERE job_id = ? AND material_id = ? AND provider_id = ? AND status = 'pending'
            """,
            (quote_amount, quote_currency, message_body, whatsapp_message_id,
             job_id, material_id, provider_id),
            cursor=cursor,
            commit=True
        )
        current_app.logger.info(f"Updated provider_quotes for job {job_id}, material {material_id}, provider {provider_id} with amount {quote_amount}")
        # Update the log with the determined job_id, material_id, provider_id
        save_whatsapp_log(
            job_id=job_id, material_id=material_id, provider_id=provider_id,
            direction='inbound', from_number=from_number,
            to_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
            message_body=message_body, whatsapp_message_id=whatsapp_message_id,
            status='processed' # Mark as processed after updating quote
        )
    else:
        current_app.logger.warning(f"Not enough info to update provider_quotes. Job: {job_id}, Material: {material_id}, Provider: {provider_id}, Amount: {quote_amount}")
        # If we couldn't update the quote, log the message with the determined IDs but status 'unprocessed'
        save_whatsapp_log(
            job_id=job_id, material_id=material_id, provider_id=provider_id,
            direction='inbound', from_number=from_number,
            to_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
            message_body=message_body, whatsapp_message_id=whatsapp_message_id,
            status='unprocessed', error_info='Failed to update provider_quotes'
        )

@whatsapp_meta_bp.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    to = data.get('to')
    body = data.get('body')
    job_id = data.get('job_id')
    material_id = data.get('material_id')
    provider_id = data.get('provider_id')

    if not all([to, body]):
        return jsonify({"status": "error", "message": "Missing 'to' or 'body'"}), 400

    try:
        message_id = send_whatsapp_text(to, body)
        if message_id:
            # Save outbound message log
            save_whatsapp_log(
                job_id=job_id,
                material_id=material_id,
                provider_id=provider_id,
                direction='outbound',
                from_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'), # Assuming this is the sending number
                to_number=to,
                message_body=body,
                whatsapp_message_id=message_id,
                status='sent'
            )
            return jsonify({"status": "success", "message_id": message_id}), 200
        else:
            save_whatsapp_log(
                job_id=job_id,
                material_id=material_id,
                provider_id=provider_id,
                direction='outbound',
                from_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
                to_number=to,
                message_body=body,
                status='failed',
                error_info='Failed to get message ID from WhatsApp API'
            )
            return jsonify({"status": "error", "message": "Failed to send message"}), 500
    except Exception as e:
        current_app.logger.error(f"Error sending WhatsApp message: {e}")
        save_whatsapp_log(
            job_id=job_id,
            material_id=material_id,
            provider_id=provider_id,
            direction='outbound',
            from_number=current_app.config.get('WHATSAPP_PHONE_NUMBER_ID'),
            to_number=to,
            message_body=body,
            status='failed',
            error_info=str(e)
        )
        return jsonify({"status": "error", "message": str(e)}), 500
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "koal-verify-2025")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")

def verify_signature(raw_body: bytes, header_sig: str) -> bool:
    """Verifica la firma de los webhooks de Meta para asegurar la autenticidad del remitente."""
    if not APP_SECRET or not header_sig:
        current_app.logger.warning("APP_SECRET o X-Hub-Signature-256 no configurados/recibidos. Saltando verificación de firma.")
        return True  # En desarrollo, podemos omitir si no está configurado
    mac = hmac.new(APP_SECRET.encode(), msg=raw_body, digestmod=hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, header_sig)

@whatsapp_meta_bp.get("")
def verify():
    """Endpoint para la verificación inicial del webhook de Meta."""
    # Meta verification challenge
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        current_app.logger.info("Webhook verificado correctamente.")
        return challenge, 200
    current_app.logger.warning("Error de verificación de webhook: Modo o token incorrecto.")
    return "Error de verificación", 403

@whatsapp_meta_bp.post("")
def receive():
    """Endpoint para recibir mensajes entrantes de WhatsApp y procesar respuestas de proveedores."""
    raw = request.get_data()
    if not verify_signature(raw, request.headers.get("X-Hub-Signature-256", "")):
        current_app.logger.warning("Firma de webhook inválida.")
        return "Firma inválida", 403

    payload = request.get_json(force=True, silent=True) or {}
    current_app.logger.info(f"[WA] incoming: {json.dumps(payload, ensure_ascii=False)}")

    db = get_db()
    if db is None:
        current_app.logger.error("Database connection failed in WhatsApp webhook.")
        return "Internal Server Error", 500

    # Extrae mensajes entrantes
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                from_ = msg.get("from")            # número del cliente/proveedor
                body  = (msg.get("text", {}) or {}).get("body", "")
                current_app.logger.info(f"[WA] {from_} dice: {body}")

                # --- Logic to parse supplier responses ---
                # 1. Find a pending quote request from this provider
                provider = db.execute('SELECT id FROM proveedores WHERE whatsapp_number = ?', (from_,)).fetchone()
                if provider:
                    pending_quote = db.execute(
                        'SELECT id, material_id, requested_qty FROM provider_quotes WHERE provider_id = ? AND status = ? ORDER BY created_at DESC LIMIT 1',
                        (provider['id'], 'pending')
                    ).fetchone()

                    if pending_quote:
                        # Try to parse price and date from the message body
                        price_match = re.search(r'(\d+[.,]?\d*)\s*(€|eur|euros)', body, re.IGNORECASE)
                        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', body)

                        quoted_price = float(price_match.group(1).replace(',', '.')) if price_match else None
                        promised_date = date_match.group(1) if date_match else None

                        status = 'quoted'
                        if re.search(r'no\s*stock', body, re.IGNORECASE):
                            status = 'no_stock'

                        db.execute(
                            '''UPDATE provider_quotes SET
                               response_msg_id = ?, quote_amount = ?, promised_date = ?, status = ?, raw_text = ?, updated_at = datetime('now')
                               WHERE id = ?''',
                            (msg.get('id'), quoted_price, promised_date, status, body, pending_quote['id'])
                        )
                        db.commit()
                        current_app.logger.info(f"[WA] Updated quote {pending_quote['id']} from {from_} with status {status}.")
                    else:
                        current_app.logger.info(f"[WA] Received message from {from_} but no pending quote found.")
                else:
                    current_app.logger.info(f"[WA] Received message from unknown provider: {from_}")

                # --- End Logic to parse supplier responses ---

    return "ok", 200