# backend/whatsapp/__init__.py
import os
import json
from typing import Optional, Dict
from flask import current_app
from backend.db_utils import get_db

def save_whatsapp_log(direction: str, phone: Optional[str], message: Optional[str],
                      provider: str, status: str, error: Optional[str]=None,
                      payload: Optional[Dict]=None):
    db = get_db()
    if db is None:
        current_app.logger.warning("DB not available for whatsapp log")
        return
    db.execute(
        "INSERT INTO whatsapp_logs (direction, phone, message, provider, status, error, payload) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (direction, phone, message, provider, status, error, json.dumps(payload or {}))
    )
    db.commit()

class WhatsAppClient:
    def __init__(self):
        self.provider = (os.getenv("WHATSAPP_PROVIDER") or "meta").lower()
        self.dry_run = (os.getenv("WHATSAPP_DRY_RUN", "0") == "1")

        if self.provider == "meta":
            from backend.whatsapp_meta import MetaWhatsApp
            self.impl = MetaWhatsApp()
        elif self.provider == "twilio":
            from backend.whatsapp_twilio import TwilioWhatsApp
            self.impl = TwilioWhatsApp()
        else:
            raise ValueError(f"Unknown WHATSAPP_PROVIDER={self.provider}")

    def send_text(self, to_phone: str, text: str) -> Dict:
        if self.dry_run:
            current_app.logger.info(f"[DRY-RUN] WA -> {to_phone}: {text}")
            save_whatsapp_log("outbound", to_phone, text, self.provider, "dry_run", None, {"dry_run": True})
            return {"ok": True, "dry_run": True}

        try:
            resp = self.impl.send_text(to_phone, text)
            status = resp.get("status", "sent")
            save_whatsapp_log("outbound", to_phone, text, self.provider, status, None, resp)
            return resp
        except Exception as e:
            current_app.logger.exception("Error sending WhatsApp")
            save_whatsapp_log("outbound", to_phone, text, self.provider, "error", str(e))
            return {"ok": False, "error": str(e)}
