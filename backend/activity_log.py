
from flask import g
from sqlalchemy import text
from backend.extensions import db

def add_activity_log(action, entity_type=None, entity_id=None, details=""):
    """Helper function to add an entry to the activity log."""
    try:
        user_id = g.user.id if hasattr(g, 'user') and g.user.is_authenticated else None
        log_entry = {
            'user_id': user_id,
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'details': details
        }
        db.session.execute(
            text("""INSERT INTO actividad_log (user_id, action, entity_type, entity_id, details)
                     VALUES (:user_id, :action, :entity_type, :entity_id, :details)"""),
            log_entry
        )
        db.session.commit()
    except Exception as e:
        # In case of error, we don't want to crash the main operation
        current_app.logger.error(f"Error al añadir al registro de actividad: {e}")
        db.session.rollback()
