from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import text

from backend.auth import login_required
from backend.extensions import db
from backend.models import get_table_class

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@login_required
def index():
    return render_template("reports/index.html", title="Informes")


@bp.route("/financial")
@login_required
def financial_reports():
    return render_template("reports/financial.html", title="Informes Financieros")


@bp.route("/commissions")
@login_required
def commission_reports():
    Comision = get_table_class("comisiones")
    User = get_table_class("users")
    Ticket = get_table_class("tickets")
    Client = get_table_class("clientes")

    commissions = db.session.execute(
        text(
            """
            SELECT 
                c.id, 
                c.monto_comision, 
                c.porcentaje, 
                c.estado, 
                c.fecha_generacion,
                u.username AS comercial_name,
                t.titulo AS job_title,
                cl.nombre AS client_name
            FROM comisiones c
            JOIN users u ON c.socio_comercial_id = u.id
            LEFT JOIN tickets t ON c.ticket_id = t.id
            LEFT JOIN clientes cl ON t.cliente_id = cl.id
            ORDER BY c.fecha_generacion DESC
            """
        )
    ).fetchall()

    return render_template("reports/commissions.html", title="Informes de Comisiones", commissions=commissions)

