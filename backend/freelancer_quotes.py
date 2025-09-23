import functools
import json

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('freelancer_quotes', __name__, url_prefix='/freelancer_quotes')

@bp.route('/')
@login_required
def list_freelancer_quotes():
    db = get_db()
    # Only show quotes created by or assigned to the current freelancer
    quotes = db.execute(
        '''SELECT p.id, p.ticket_id, p.estado, p.total, p.pdf_url, p.aceptado_en, c.nombre as client_name
           FROM presupuestos p JOIN clientes c ON p.ticket_id = c.id
           WHERE p.freelancer_id = ? ORDER BY p.aceptado_en DESC''',
        (g.user.id,)
    ).fetchall()
    return render_template('freelancer_quotes/list.html', quotes=quotes)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_freelancer_quote():
    db = get_db()
    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    tickets = db.execute('SELECT id, descripcion FROM tickets ORDER BY descripcion').fetchall()

    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id', type=int)
        estado = request.form.get('estado')
        total = request.form.get('total', type=float)
        # For now, pdf_url and aceptado_en will be handled later
        
        error = None

        if not ticket_id or not estado or not total:
            error = 'Ticket, estado y total son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''INSERT INTO presupuestos (ticket_id, freelancer_id, estado, total)
                       VALUES (?, ?, ?, ?)''',
                    (ticket_id, g.user.id, estado, total)
                )
                db.commit()
                flash('¡Presupuesto añadido correctamente!')
                return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('freelancer_quotes/form.html', quote=None, clients=clients, tickets=tickets)
