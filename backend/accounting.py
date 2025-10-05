import csv
from io import StringIO

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from backend.auth import login_required
from backend.db import get_db

bp = Blueprint('accounting', __name__, url_prefix='/accounting')

@bp.route('/report', methods=('GET', 'POST'))
@login_required
def accounting_report():
    # Permission check (e.g., only admin/oficina can access)
    if not (g.user.has_permission('view_reports') or g.user.has_permission('manage_all_jobs')):
        flash('No tienes permiso para acceder a los informes contables.', 'error')
        return redirect(url_for('index'))

    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    report_data = []
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    transaction_type = request.form.get('transaction_type')

    if request.method == 'POST':
        query = "SELECT * FROM financial_transactions WHERE 1=1"
        params = []

        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date)
        if transaction_type and transaction_type != 'all':
            query += " AND type = ?"
            params.append(transaction_type)

        try:
            report_data = db.execute(query, params).fetchall()
        except Exception as e:
            flash(f'Error generating report: {e}', 'error')
            current_app.logger.error(f"Error generating accounting report: {e}", exc_info=True)
            report_data = [] # Clear data on error

        if 'download_csv' in request.form:
            si = StringIO()
            cw = csv.writer(si)

            # Write headers
            headers = ['ID', 'Tipo', 'Monto', 'IVA %', 'Monto IVA', 'Total', 'Descripción', 'Fecha', 'Registrado Por', 'ID Trabajo']
            cw.writerow(headers)

            # Write data rows
            for row in report_data:
                total_with_vat = row['amount'] + (row['vat_amount'] if row['vat_amount'] is not None else 0)
                cw.writerow([
                    row['id'],
                    row['type'],
                    f"{row['amount']:.2f}",
                    f"{row['vat_rate']:.2f}" if row['vat_rate'] is not None else '0.00',
                    f"{row['vat_amount']:.2f}" if row['vat_amount'] is not None else '0.00',
                    f"{total_with_vat:.2f}",
                    row['description'],
                    row['transaction_date'],
                    row['recorded_by'],
                    row['ticket_id']
                ])

            output = make_response(si.getvalue())
            output.headers["Content-Disposition"] = "attachment; filename=informe_contable.csv"
            output.headers["Content-type"] = "text/csv"
            return output

    return render_template('accounting/report_form.html', report_data=report_data, start_date=start_date, end_date=end_date, transaction_type=transaction_type)
