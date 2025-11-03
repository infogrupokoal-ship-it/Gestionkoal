# backend/audit_log.py

import json

from flask import g

from backend.db_utils import get_db


def log_activity(action: str, entity: str, entity_id: int = None, diff: dict = None):
    """
    Logs an activity to the auditoria table.

    Args:
        action (str): Description of the action (e.g., 'create_user', 'update_ticket_status').
        entity (str): Type of entity affected (e.g., 'user', 'ticket', 'expense').
        entity_id (int, optional): ID of the entity affected. Defaults to None.
        diff (dict, optional): Dictionary representing the changes made. Defaults to None.
    """
    db = get_db()
    if db is None:
        # Cannot log if DB is not available
        return

    actor_id = g.user.id if g.user.is_authenticated else None
    diff_json = json.dumps(diff) if diff else None

    try:
        db.execute(
            "INSERT INTO auditoria (actor_id, accion, entidad, entidad_id, diff) VALUES (?, ?, ?, ?, ?)",
            (actor_id, action, entity, entity_id, diff_json),
        )
        db.commit()
    except Exception as e:
        # Log to console if audit logging itself fails
        print(f"ERROR: Failed to log activity to DB: {e}")
