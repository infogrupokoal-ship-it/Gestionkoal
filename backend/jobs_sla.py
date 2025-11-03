# backend/jobs_sla.py
from __future__ import annotations

from datetime import UTC, datetime

from flask import current_app
from sqlalchemy import text

from backend.extensions import db


def _parse_iso_dt(value):
    """Devuelve un datetime con tz; tolera cadenas ISO con o sin 'Z'."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    raise TypeError("Tipo de fecha SLA no soportado")


def run_sla_checker() -> None:
    """
    Marca eventos de incumplimiento SLA si 'now' > 'sla_due' y aún no existe evento 'breach'.
    Requiere tablas: tickets(id, sla_due) y sla_events(ticket_id, event, details).
    """
    try:
        rows = db.session.execute(
            text("SELECT id, sla_due FROM tickets WHERE sla_due IS NOT NULL")
        ).fetchall()

        for ticket_id, sla_due in rows:
            try:
                due = _parse_iso_dt(sla_due)
                now = datetime.now(UTC)
                if now <= due:
                    continue

                # ¿Existe ya evento 'breach'?
                breach_event = db.session.execute(
                    text(
                        "SELECT id FROM sla_events "
                        "WHERE ticket_id = :ticket_id AND event = 'breach'"
                    ),
                    {"ticket_id": ticket_id},
                ).fetchone()

                if not breach_event:
                    db.session.execute(
                        text(
                            "INSERT INTO sla_events (ticket_id, event, details) "
                            "VALUES (:ticket_id, :event, :details)"
                        ),
                        {
                            "ticket_id": ticket_id,
                            "event": "breach",
                            "details": "SLA incumplido",
                        },
                    )
                    db.session.commit()

            except (ValueError, TypeError):
                # sla_due inválido → saltamos sin romper el job
                continue

    except Exception as e:  # pragma: no cover
        current_app.logger.error(f"Error en run_sla_checker: {e}", exc_info=True)
