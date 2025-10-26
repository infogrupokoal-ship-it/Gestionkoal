from flask import Blueprint, render_template, current_app
from sqlalchemy import text
from backend.extensions import db


bp = Blueprint('twilio_wa', __name__, url_prefix='/whatsapp')


@bp.route('/logs')
def list_whatsapp_logs():
    status = (request.args.get('status') or '').strip()
    q = (request.args.get('q') or '').strip()
    try:
        base_sql = "SELECT id, whatsapp_message_id, status, timestamp, from_number FROM whatsapp_message_logs"
        where = []
        params = {}
        if status:
            where.append("status = :status")
            params['status'] = status
        if q:
            where.append("from_number LIKE :q")
            params['q'] = f"%{q}%"
        if where:
            base_sql += " WHERE " + " AND ".join(where)
        base_sql += " ORDER BY id DESC LIMIT 200"
        rows = db.session.execute(text(base_sql), params).fetchall()
    except Exception:
        current_app.logger.warning("Failed to read whatsapp_message_logs; falling back to empty list", exc_info=True)
        rows = []

    def mask(num: str | None) -> str:
        if not num:
            return ""
        last4 = num[-4:]
        return f"***{last4}"

    logs = [
        {
            "id": r.id,
            "message_id": getattr(r, 'whatsapp_message_id', None),
            "status": getattr(r, 'status', None),
            "timestamp": getattr(r, 'timestamp', None),
            "from_number_hash": mask(getattr(r, 'from_number', None)),
        }
        for r in rows
    ]

    return render_template('whatsapp_message_logs/list.html', logs=logs, status=status, q=q)
