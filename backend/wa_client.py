import os, requests

GRAPH_BASE = "https://graph.facebook.com/v22.0"
PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

def send_whatsapp_text(to_e164: str, text: str):
    """Envía un mensaje de texto de WhatsApp a un número específico."""
    url = f"{GRAPH_BASE}/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_e164,         # ejemplo: "346xxxxxxxx"
        "type": "text",
        "text": {"body": text}
    }
    r = requests.post(url, headers=headers, json=data, timeout=30)
    r.raise_for_status()
    return r.json()

def send_whatsapp_template(to_e164: str, template_name: str, lang="es"):
    """Envía un mensaje de plantilla de WhatsApp a un número específico."""
    url = f"{GRAPH_BASE}/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_e164,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang}
        }
    }
    r = requests.post(url, headers=headers, json=data, timeout=30)
    r.raise_for_status()
    return r.json()
