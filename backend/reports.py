
from flask import Blueprint, render_template

from backend.auth import login_required

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/financial')
@login_required
def financial_reports():
    return render_template('reports/financial.html', title="Informes Financieros")
