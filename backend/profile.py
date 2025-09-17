import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from backend.auth import login_required

bp = Blueprint('profile', __name__, url_prefix='/profile')

@bp.route('/')
@login_required
def user_profile():
    # Assuming current_user is available from Flask-Login
    return render_template('users/profile.html', user=g.user, roles=[])
