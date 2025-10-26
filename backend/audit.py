from flask import Blueprint, current_app, render_template, request
from sqlalchemy import text
from backend.extensions import db


bp = Blueprint('audit', __name__, url_prefix='/audit')


@bp.route('/logs')
def list_logs():
    f_type = (request.args.get('type') or '').strip().lower()
    q = (request.args.get('q') or '').strip().lower()
    start = (request.args.get('start') or '').strip()
    end = (request.args.get('end') or '').strip()
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
    # Optional filters in Python to keep it simple
    if f_type:
        items = [it for it in items if (it.get('type') or '').lower() == f_type]
    if q:
        qq = q.lower()
        items = [it for it in items if qq in str(it.get('details') or '').lower() or qq in str(it.get('summary') or '').lower()]
    # Basic date range filter (string compare on ISO-like timestamps)
    if start:
        items = [it for it in items if str(it.get('ts') or '') >= start]
    if end:
        items = [it for it in items if str(it.get('ts') or '') <= end]

    try:
        items.sort(key=lambda x: (x.get('ts') or ''), reverse=True)
    except Exception:
        pass
    return render_template('audit/logs.html', items=items, f_type=f_type, q=q, start=start, end=end)
