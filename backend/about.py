import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

bp = Blueprint('about', __name__, url_prefix='/about')

@bp.route('/')
def about():
    return render_template('about.html')
