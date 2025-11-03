import hashlib
import hmac
import json
import os

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.ai_orchestrator import process_incoming_text
from backend.extensions import db
from backend.utils.ratelimit import rate_limit

bp = Blueprint("whatsapp_webhook", __name__, url_prefix="/webhooks/whatsapp")
bp_alias = Blueprint("whatsapp_webhook_alias", __name__, url_prefix="/webhook/whatsapp")
_SEEN_MESSAGE_IDS = set()


def _is_dry_run() -> bool:
    value = current_app.config.get("WHATSAPP_DRY_RUN")
    if value is None:
        value = os.getenv("WHATSAPP_DRY_RUN", "0")
    return str(value).lower() in {"1", "true", "yes", "on"}


@bp.route("/", methods=["GET"])
@bp_alias.route("/", methods=["GET"])
def verify():
    # Meta verification
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token and token == verify_token:
        current_app.logger.info(f"Webhook verified: {challenge}")
        return challenge, 200

    current_app.logger.warning(
        f"Webhook verification failed. Mode: {mode}, Token: {token}"
    )
    return "forbidden", 403


@bp.route("/", methods=["POST"])
@bp_alias.route("/", methods=["POST"])
@rate_limit(calls=10, per_seconds=60)
def receive():
    # Raw body for signature verification
    raw_body = request.get_data(cache=True) or b""
    app_secret = os.getenv("WHATSAPP_APP_SECRET")

    # If app secret is set, verify X-Hub-Signature-256
    if app_secret:
        try:
            sig_header = request.headers.get("X-Hub-Signature-256", "")
            if not sig_header.startswith("sha256="):
                current_app.logger.warning(
                    "Missing or malformed X-Hub-Signature-256 header"
                )
                return jsonify({"ok": False, "error": "invalid signature"}), 401
            expected = (
                "sha256="
                + hmac.new(
                    app_secret.encode("utf-8"), raw_body, hashlib.sha256
                ).hexdigest()
            )
            if not hmac.compare_digest(sig_header, expected):
                current_app.logger.warning("Signature mismatch for WhatsApp webhook")
                return jsonify({"ok": False, "error": "invalid signature"}), 401
        except Exception:
            current_app.logger.exception("Failed to verify WhatsApp webhook signature")
            return jsonify({"ok": False, "error": "signature verification failed"}), 401
    else:
        current_app.logger.info(
            "WHATSAPP_APP_SECRET not set; skipping signature verification"
        )

    data = request.get_json(silent=True) or {}

    dry_run = _is_dry_run()
    try:
        phone, text_msg, message_id = None, None, None

        # Meta Cloud typical structure
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", []) or []
        if messages:
            msg = messages[0]
            phone = msg.get("from")
            message_id = msg.get("id") or msg.get("wamid")
            if msg.get("type") == "text":
                text_msg = (msg.get("text") or {}).get("body")

        # Idempotency: if message_id already processed, return OK
        if message_id:
            # Lightweight in-memory idempotency to support environments sin tabla
            if message_id in _SEEN_MESSAGE_IDS:
                current_app.logger.info(
                    f"Duplicate webhook message ignored (message_id={message_id})"
                )
                return jsonify({"ok": True, "duplicate": True}), 200
            _SEEN_MESSAGE_IDS.add(message_id)
            try:
                exists = db.session.execute(
                    text(
                        "SELECT id FROM whatsapp_message_logs WHERE whatsapp_message_id = :mid LIMIT 1"
                    ),
                    {"mid": message_id},
                ).fetchone()
                if exists:
                    current_app.logger.info(
                        f"Duplicate webhook message ignored (message_id={message_id})"
                    )
                    return jsonify({"ok": True, "duplicate": True}), 200
            except Exception:
                current_app.logger.warning(
                    "Idempotency check failed; proceeding without it", exc_info=True
                )

        # Log inbound message (best-effort, con idempotencia por índice único)
        try:
            db.session.execute(
                text(
                    "INSERT INTO whatsapp_message_logs (direction, from_number, to_number, message_body, whatsapp_message_id, status) "
                    "VALUES (:direction, :from_number, :to_number, :message_body, :whatsapp_message_id, :status)"
                ),
                {
                    "direction": "inbound",
                    "from_number": phone,
                    "to_number": None,
                    "message_body": text_msg or json.dumps(data)[:1000],
                    "whatsapp_message_id": message_id,
                    "status": "received",
                },
            )
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            current_app.logger.info(
                f"Duplicate inbound log ignored by unique index (message_id={message_id})"
            )
            return jsonify({"ok": True, "duplicate": True}), 200
        except Exception:
            db.session.rollback()
            current_app.logger.warning(
                "Failed to log inbound WhatsApp message", exc_info=True
            )

        # If we have a text message, process it with the AI orchestrator (unless dry-run)
        if text_msg and phone:
            if dry_run:
                current_app.logger.info(
                    "WHATSAPP_DRY_RUN=1: inbound payload stored but AI flow skipped."
                )
            else:
                current_app.logger.info(
                    f"Processing incoming text from {phone} via AI orchestrator."
                )
                try:
                    process_incoming_text(
                        source="whatsapp", raw_phone=phone, message_text=text_msg
                    )
                except Exception:
                    current_app.logger.exception(
                        "AI orchestrator error; continuing with 200 response"
                    )

                # Mark inbound as processed (best-effort)
                if message_id:
                    try:
                        db.session.execute(
                            text(
                                "UPDATE whatsapp_message_logs SET status = :status WHERE whatsapp_message_id = :mid"
                            ),
                            {"status": "processed", "mid": message_id},
                        )
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                        current_app.logger.warning(
                            "Failed to mark inbound message as processed", exc_info=True
                        )

        return jsonify({"ok": True, "dry_run": dry_run}), 200
    except Exception:
        current_app.logger.exception("Error processing WA webhook")
        # Fallback to 200 to avoid provider retries during tests/dev
        return jsonify({"ok": False, "dry_run": dry_run}), 200
