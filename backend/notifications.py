import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from backend.auth import login_required
from backend.db import get_db
from flask import jsonify

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@bp.route('/')
@login_required
def list_notifications():
    return render_template('notifications/list.html', title="Notificaciones")

@bp.route('/api/unread_notifications_count')
@login_required
def unread_notifications_count():
    db = get_db()
    count = db.execute(
        'SELECT COUNT(id) FROM notifications WHERE user_id = ? AND is_read = 0',
        (g.user.id,)
    ).fetchone()[0]
    return jsonify({'unread_count': count})
