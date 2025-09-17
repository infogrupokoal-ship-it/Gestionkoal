import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from backend.auth import login_required

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/financial')
@login_required
def financial_reports():
    return render_template('reports/financial.html', title="Informes Financieros")
