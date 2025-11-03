# backend/whatsapp_meta.py
import os

import requests
from flask import current_app


class MetaWhatsApp:
    """WhatsApp client for Meta (Facebook) Graph API."""

    def __init__(self):
        self.graph_base = "https://graph.facebook.com/v22.0"
        self.phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        if not all([self.phone_id, self.access_token]):
            current_app.logger.warning(
                "Meta WhatsApp credentials not fully configured."
            )

    def send_text(self, to_phone: str, text: str) -> dict:
        """Envía un mensaje de texto de WhatsApp a un número específico."""
        if not all([self.phone_id, self.access_token]):
            raise ValueError("Meta WhatsApp client is not configured.")

        url = f"{self.graph_base}/{self.phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": text},
        }

        try:
            r = requests.post(url, headers=headers, json=data, timeout=30)
            r.raise_for_status()
            response_data = r.json()
            # Add a status for consistency with the abstract client
            response_data["status"] = "sent"
            return response_data
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Failed to send Meta WhatsApp message: {e}")
            return {"ok": False, "error": str(e), "status": "failed"}
