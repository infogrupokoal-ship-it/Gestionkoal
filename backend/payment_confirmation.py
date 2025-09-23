from datetime import datetime, timedelta
import os
import secrets

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import login_required

from backend.db import get_db
from backend.notifications import send_whatsapp_notification

bp = Blueprint('payment_confirmation', __name__, url_prefix='/payment')

@bp.route('/confirm/<int:ticket_id>/<token>', methods=('GET', 'POST'))
def confirm_payment(ticket_id, token):
    db = get_db()
    ticket = db.execute(
        'SELECT id, cliente_id, estado_pago, payment_confirmation_token, payment_confirmation_expires FROM tickets WHERE id = ?',
        (ticket_id,)
    ).fetchone()

    if ticket is None:
        flash('Enlace de confirmación de pago no válido.', 'error')
        return render_template('payment_confirmation/confirm.html', message='Enlace no válido.')

    if ticket['estado_pago'] == 'Pagado':
        flash('Este pago ya ha sido confirmado.', 'info')
        return render_template('payment_confirmation/confirm.html', message='Pago ya confirmado.')

    if ticket['payment_confirmation_token'] != token:
        flash('Token de confirmación no válido.', 'error')
        return render_template('payment_confirmation/confirm.html', message='Token no válido.')

    if datetime.now() > datetime.strptime(ticket['payment_confirmation_expires'], '%Y-%m-%d %H:%M:%S'):
        flash('El enlace de confirmación ha expirado.', 'error')
        return render_template('payment_confirmation/confirm.html', message='Enlace expirado.')

    if request.method == 'POST':
        try:
            db.execute(
                'UPDATE tickets SET estado_pago = 'Pagado' WHERE id = ?',
                (ticket_id,)
            )
            db.commit()
            flash('¡Pago confirmado con éxito! Gracias.', 'success')
            return render_template('payment_confirmation/success.html', ticket_id=ticket_id)
        except Exception as e:
            flash(f'Ocurrió un error al confirmar el pago: {e}', 'error')
            db.rollback()

    return render_template('payment_confirmation/confirm.html', ticket=ticket)
