from flask import Blueprint, current_app, render_template
from sqlalchemy import text
from backend.extensions import db


bp = Blueprint('audit', __name__, url_prefix='/audit')


@bp.route('/logs')
def list_logs():
    items = []
    try:
        rows = db.session.execute(
            text("SELECT time as ts, message as details FROM error_log ORDER BY id DESC LIMIT 100")
        ).fetchall()
        for r in rows:
            items.append({
                'ts': getattr(r, 'ts', None) or getattr(r, 'time', None),
                'type': 'error',
                'summary': 'error_log',
                'details': getattr(r, 'details', None) or getattr(r, 'message', None),
            })
    except Exception:
        current_app.logger.info('No error_log table or failed to read error_log')

    try:
        rows = db.session.execute(
            text("SELECT created_at as ts, direction||':'||status as summary, message as details FROM whatsapp_logs ORDER BY id DESC LIMIT 100")
        ).fetchall()
        for r in rows:
            items.append({
                'ts': getattr(r, 'ts', None) or getattr(r, 'created_at', None),
                'type': 'whatsapp',
                'summary': getattr(r, 'summary', None),
                'details': getattr(r, 'details', None) or getattr(r, 'message', None),
            })
    except Exception:
        current_app.logger.info('No whatsapp_logs table or failed to read whatsapp_logs')

    try:
        rows = db.session.execute(
            text("SELECT created_at as ts, event_type as summary, substr(output, 1, 200) as details FROM ai_logs ORDER BY id DESC LIMIT 100")
        ).fetchall()
        for r in rows:
            items.append({
                'ts': getattr(r, 'ts', None) or getattr(r, 'created_at', None),
                'type': 'ai',
                'summary': getattr(r, 'summary', None),
                'details': getattr(r, 'details', None) or getattr(r, 'output', None),
            })
    except Exception:
        current_app.logger.info('No ai_logs table or failed to read ai_logs')

    try:
        rows = db.session.execute(
            text("SELECT created_at as ts, 'notification' as summary, message as details FROM notifications ORDER BY id DESC LIMIT 100")
        ).fetchall()
        for r in rows:
            items.append({
                'ts': getattr(r, 'ts', None) or getattr(r, 'created_at', None),
                'type': 'notification',
                'summary': getattr(r, 'summary', None) or 'notification',
                'details': getattr(r, 'details', None) or getattr(r, 'message', None),
            })
    except Exception:
        current_app.logger.info('No notifications table or failed to read notifications')

    # Order by timestamp descending where possible
    try:
        items.sort(key=lambda x: (x.get('ts') or ''), reverse=True)
    except Exception:
        pass

    return render_template('audit/logs.html', items=items)

