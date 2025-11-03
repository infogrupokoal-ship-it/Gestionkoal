import json
import os

from flask import current_app
from sqlalchemy import text

from backend.extensions import db


def save_whatsapp_log(
    direction: str,
    phone: str | None,
    message: str | None,
    provider: str,
    status: str,
    error: str | None = None,
    payload: dict | None = None,
):
    try:
        db.session.execute(
            text(
                "INSERT INTO whatsapp_logs (direction, phone, message, provider, status, error, payload) "
                "VALUES (:direction, :phone, :message, :provider, :status, :error, :payload)"
            ),
            {
                "direction": direction,
                "phone": phone,
                "message": message,
                "provider": provider,
                "status": status,
                "error": error,
                "payload": json.dumps(payload or {}),
            },
        )
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to write whatsapp_log: {e}")


class WhatsAppClient:
    def __init__(self):
        self.provider = (os.getenv("WHATSAPP_PROVIDER") or "meta").lower()
        self.dry_run = os.getenv("WHATSAPP_DRY_RUN", "0") == "1"
        self.impl = None

        try:
            if self.provider == "meta":
                from backend.whatsapp_meta import MetaWhatsApp

                self.impl = MetaWhatsApp()
            elif self.provider == "twilio":
                from backend.whatsapp_twilio import TwilioWhatsApp

                self.impl = TwilioWhatsApp()
            else:
                raise ValueError(f"Unknown WHATSAPP_PROVIDER={self.provider}")
        except ImportError as e:
            current_app.logger.error(
                f"Could not import WhatsApp provider implementation: {e}"
            )
            self.impl = None  # Ensure impl is None if import fails
        except Exception as e:
            current_app.logger.error(f"Failed to initialize WhatsApp provider: {e}")
            self.impl = None

    def send_text(self, to_phone: str, text: str) -> dict:
        if self.dry_run:
            current_app.logger.info(f"[DRY-RUN] WA -> {to_phone}: {text}")
            save_whatsapp_log(
                "outbound",
                to_phone,
                text,
                self.provider,
                "dry_run",
                None,
                {"dry_run": True},
            )
            return {"ok": True, "dry_run": True, "status": "dry_run"}

        if self.impl is None:
            error_msg = "WhatsApp provider not initialized"
            current_app.logger.error(error_msg)
            save_whatsapp_log(
                "outbound", to_phone, text, self.provider, "error", error_msg
            )
            return {"ok": False, "error": error_msg, "status": "error"}

        try:
            resp = self.impl.send_text(to_phone, text)
            status = resp.get("status", "sent")
            save_whatsapp_log(
                "outbound", to_phone, text, self.provider, status, None, resp
            )
            return resp
        except Exception as e:
            current_app.logger.exception("Error sending WhatsApp")
            error_str = str(e)
            save_whatsapp_log(
                "outbound", to_phone, text, self.provider, "error", error_str
            )
            return {"ok": False, "error": error_str, "status": "error"}
