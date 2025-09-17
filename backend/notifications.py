import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from backend.auth import login_required

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@bp.route('/')
@login_required
def list_notifications():
    return render_template('notifications/list.html', title="Notificaciones")
