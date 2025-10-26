from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
import csv
import io
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
    # Export CSV if requested
    if (request.args.get('export') or '').lower() == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ts', 'type', 'summary', 'details'])
        for it in items:
            writer.writerow([it.get('ts') or '', it.get('type') or '', it.get('summary') or '', (it.get('details') or '').replace('\n', ' ')])
        csv_data = output.getvalue()
        return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=audit_logs.csv'})

    # Pagination
    try:
        page = max(1, int(request.args.get('page', '1')))
    except Exception:
        page = 1
    try:
        per_page = max(1, min(200, int(request.args.get('per_page', '50'))))
    except Exception:
        per_page = 50
    total = len(items)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = items[start_idx:end_idx]
    return render_template('audit/logs.html', items=page_items, f_type=f_type, q=q, start=start, end=end, page=page, per_page=per_page, total=total)


@bp.route('/toggles', methods=['GET', 'POST'])
@login_required
def toggles():
    if not getattr(current_user, 'has_permission', lambda *_: False)('admin'):
        return ("forbidden", 403)
    cfg = current_app.config
    if request.method == 'POST':
        provider = (request.form.get('provider') or '').strip().lower() or 'meta'
        dry = request.form.get('dry_run') == 'on'
        cfg['WHATSAPP_PROVIDER'] = provider
        cfg['WHATSAPP_DRY_RUN'] = dry
        # Keep environment in sync (best-effort)
        try:
            os.environ['WHATSAPP_PROVIDER'] = provider
            os.environ['WHATSAPP_DRY_RUN'] = '1' if dry else '0'
        except Exception:
            pass
        flash('Toggles actualizados')
        return redirect(url_for('audit.toggles'))

    return render_template('audit/toggles.html',
                           provider=cfg.get('WHATSAPP_PROVIDER') or os.environ.get('WHATSAPP_PROVIDER', 'meta'),
                           dry_run=(cfg.get('WHATSAPP_DRY_RUN') if cfg.get('WHATSAPP_DRY_RUN') is not None else (os.environ.get('WHATSAPP_DRY_RUN', '0') == '1')))
