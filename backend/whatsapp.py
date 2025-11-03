# backend/whatsapp.py
import json
import os

from flask import current_app

from backend.extensions import db

# Importar los clientes específicos de cada proveedor
from backend.whatsapp_meta import MetaWhatsApp
from backend.whatsapp_twilio import TwilioWhatsApp


class WhatsAppClient:
    def __init__(self):
        cfg = getattr(current_app, "config", {})
        dry_cfg = cfg.get("WHATSAPP_DRY_RUN")
        self.dry_run = (
            (str(dry_cfg).lower() in ("1", "true"))
            if dry_cfg is not None
            else (os.environ.get("WHATSAPP_DRY_RUN", "0") == "1")
        )
        self.provider = (
            cfg.get("WHATSAPP_PROVIDER") or os.environ.get("WHATSAPP_PROVIDER", "meta")
        ).lower()

        if not self.dry_run:
            if self.provider == "meta":
                self._client = MetaWhatsApp()
            elif self.provider == "twilio":
                self._client = TwilioWhatsApp()
            else:
                current_app.logger.error(
                    f"Proveedor de WhatsApp desconocido: {self.provider}"
                )
                self._client = None
        else:
            current_app.logger.info("WhatsAppClient inicializado en modo DRY-RUN.")
            self._client = None  # No hay cliente real en dry-run

    def send_text(self, to_phone: str, text: str) -> dict:
        if self.dry_run:
            log_message = f"[DRY-RUN] WA -> {to_phone}: {text}"
            current_app.logger.info(log_message)
            # Persist best-effort log in whatsapp_logs
            try:
                db.session.execute(
                    text(
                        "INSERT INTO whatsapp_logs (direction, phone, message, provider, status, error, payload) "
                        "VALUES (:direction, :phone, :message, :provider, :status, :error, :payload)"
                    ),
                    {
                        "direction": "outbound",
                        "phone": to_phone,
                        "message": text,
                        "provider": self.provider,
                        "status": "dry_run",
                        "error": None,
                        "payload": json.dumps(
                            {"dry_run": True, "message": log_message}
                        ),
                    },
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
                current_app.logger.warning(
                    "Failed to log DRY-RUN WhatsApp message to DB", exc_info=True
                )
            return {
                "ok": True,
                "status": "dry_run",
                "payload": {"message": log_message},
            }

        if self._client:
            try:
                response = self._client.send_text(to_phone, text)
                # Persist best-effort log in whatsapp_logs
                try:
                    db.session.execute(
                        text(
                            "INSERT INTO whatsapp_logs (direction, phone, message, provider, status, error, payload) "
                            "VALUES (:direction, :phone, :message, :provider, :status, :error, :payload)"
                        ),
                        {
                            "direction": "outbound",
                            "phone": to_phone,
                            "message": text,
                            "provider": self.provider,
                            "status": response.get("status", "sent"),
                            "error": response.get("error"),
                            "payload": json.dumps(response),
                        },
                    )
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    current_app.logger.warning(
                        "Failed to log WhatsApp message to DB", exc_info=True
                    )
                return response
            except Exception as e:
                current_app.logger.error(
                    f"Error al enviar mensaje con {self.provider} client: {e}"
                )
                # Persist failure log
                try:
                    db.session.execute(
                        text(
                            "INSERT INTO whatsapp_logs (direction, phone, message, provider, status, error, payload) "
                            "VALUES (:direction, :phone, :message, :provider, :status, :error, :payload)"
                        ),
                        {
                            "direction": "outbound",
                            "phone": to_phone,
                            "message": text,
                            "provider": self.provider,
                            "status": "failed",
                            "error": str(e),
                            "payload": json.dumps({}),
                        },
                    )
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    current_app.logger.warning(
                        "Failed to log WhatsApp failure to DB", exc_info=True
                    )
                return {"ok": False, "status": "failed", "error": str(e)}
        else:
            error_msg = (
                "WhatsApp client no configurado o en modo DRY-RUN sin cliente real."
            )
            current_app.logger.error(error_msg)
            return {"ok": False, "status": "failed", "error": error_msg}
