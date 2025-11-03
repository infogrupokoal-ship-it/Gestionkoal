# backend/whatsapp_twilio.py
import os

from flask import current_app
from twilio.rest import Client


class TwilioWhatsApp:
    """WhatsApp client for Twilio API."""

    def __init__(self):
        self.sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.token = os.getenv("TWILIO_AUTH_TOKEN")
        self.wa_from = os.getenv("TWILIO_WHATSAPP_FROM")
        if not all([self.sid, self.token, self.wa_from]):
            current_app.logger.warning(
                "Twilio WhatsApp credentials not fully configured."
            )
        else:
            self.client = Client(self.sid, self.token)

    def send_text(self, to_phone: str, text: str) -> dict:
        """Envía un mensaje de texto de WhatsApp a un número específico."""
        if not hasattr(self, "client"):
            raise ValueError("Twilio WhatsApp client is not configured.")

        try:
            message = self.client.messages.create(
                from_=self.wa_from, to=f"whatsapp:{to_phone}", body=text
            )
            return {"ok": True, "sid": message.sid, "status": message.status}
        except Exception as e:
            current_app.logger.error(f"Failed to send Twilio WhatsApp message: {e}")
            return {"ok": False, "error": str(e), "status": "failed"}
