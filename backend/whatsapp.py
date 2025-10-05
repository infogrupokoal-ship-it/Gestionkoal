# backend/whatsapp.py
import hashlib
import hmac
import os

import requests
from flask import Blueprint, abort, current_app, jsonify, request

whatsapp_bp = Blueprint("whatsapp", __name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"  # usa la versión que tengas disponible

def _cfg(key, default=None):
    return os.environ.get(key, current_app.config.get(key, default))

def send_whatsapp_text(to_number: str, body: str):
    """
    Enviar texto por Cloud API.
    to_number: '34633660438' (sin +, en E.164 se suele usar +34..., Cloud API admite ambos; usa formato internacional)
    """
    phone_id = _cfg("WHATSAPP_PHONE_NUMBER_ID")
    token    = _cfg("WHATSAPP_ACCESS_TOKEN")
    url = f"{GRAPH_BASE}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body}
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

@whatsapp_bp.get("/whatsapp")
def verify():
    # Webhook verification (Meta)
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == _cfg("WHATSAPP_VERIFY_TOKEN"):
        return challenge, 200
    return "forbidden", 403

def _verify_signature(raw_body: bytes) -> bool:
    # Verificación de firma opcional (recomendado)
    app_secret = _cfg("WHATSAPP_APP_SECRET")
    signature = request.headers.get("X-Hub-Signature-256", "").replace("sha256=", "")
    if not app_secret or not signature:
        return True  # si no tienes secret configurado, omite (no recomendado en prod)
    mac = hmac.new(app_secret.encode(), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)

@whatsapp_bp.post("/whatsapp")
def receive():
    raw = request.get_data()
    if not _verify_signature(raw):
        abort(403)

    data = request.get_json(silent=True) or {}
    # Extraer mensajes entrantes (estructura de Meta)
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                msgs = value.get("messages", [])
                for m in msgs:
                    if m.get("type") == "text":
                        from_number = m["from"]           # e.g., "34633660438"
                        # wamid = m.get("id")               # deduplicación - Removed unused variable
                        text  = m["text"]["body"].strip()

                        # 1) Alta / Baja
                        if text.upper() == "ALTA":
                            handle_opt_in(from_number)
                            send_whatsapp_text(from_number, "✅ Alta confirmada. Podrás recibir avisos por aquí. Escribe ‘pedido’ o ‘aviso’ para crear uno.")
                            continue
                        if text.upper() == "BAJA":
                            handle_opt_out(from_number)
                            send_whatsapp_text(from_number, "🛑 Baja confirmada. No recibirás más mensajes. Para reactivar escribe ALTA.")
                            continue

                        # 2) Nuevo aviso/pedido (detección simple + ejemplo)
                        if any(k in text.lower() for k in ["aviso", "trabajo", "pedido"]):
                            ticket_id = create_ticket_from_text(from_number, text)
                            send_whatsapp_text(
                                from_number,
                                f"✅ Aviso creado #{ticket_id}.\nResumen: {resumen_corto(text)}\nTe avisaremos por este canal."
                            )
                        else:
                            # 3) Ayuda genérica
                            send_whatsapp_text(
                                from_number,
                                "Hola 👋 Soy Gestión Koal. Escribe:\n• ALTA para aceptar comunicaciones\n• BAJA para dejar de recibir\n• ‘pedido’ o ‘aviso’ + descripción para crear uno"
                            )
        return jsonify({"ok": True})
    except Exception as e:
        current_app.logger.exception("WhatsApp webhook error: %s", e)
        return jsonify({"ok": False}), 500

# ------------ Helpers de negocio (adapta a tu modelo real) -------------
def handle_opt_in(number: str):
    # TODO: guarda consentimiento con timestamp (GDPR)
    pass

def handle_opt_out(number: str):
    # TODO: marca opt-out en tu BD
    pass

def resumen_corto(texto: str, n=100):
    return (texto[:n] + "…") if len(texto) > n else texto

def create_ticket_from_text(number: str, texto: str) -> int:
    """
    Aquí puedes:
    - Intentar parseo rápido con regex
    - O llamar a tu IA para extraer JSON estructurado (cliente, dirección, prioridad, fecha…)
    - Crear el Aviso/Pedido en la BD y devolver el id
    """
    # TODO: implementa creación real y devuelve id
    return 1234
