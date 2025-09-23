import functools
import json
import os
from werkzeug.utils import secure_filename

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
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
    providers = db.execute('SELECT id, nombre FROM proveedores ORDER BY nombre').fetchall()
    freelancers_list = db.execute('SELECT u.id, u.username FROM users u JOIN freelancers f ON u.id = f.user_id ORDER BY u.username').fetchall()

    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id', type=int)
        estado = request.form.get('estado')
        total = request.form.get('total', type=float)
        billing_entity_type = request.form.get('billing_entity_type')
        billing_entity_id = request.form.get('billing_entity_id', type=int)
        pdf_url = None

        if 'quote_file' in request.files:
            quote_file = request.files['quote_file']
            if quote_file.filename != '':
                allowed_extensions = {'pdf'}
                if '.' in quote_file.filename and \
                   quote_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(quote_file.filename)
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True) # Ensure upload folder exists
                    file_path = os.path.join(upload_folder, filename)
                    quote_file.save(file_path)
                    pdf_url = url_for('uploaded_file', filename=filename) # Store URL path
                else:
                    error = 'Tipo de archivo no permitido para el presupuesto (solo PDF).

        error = None

        if not ticket_id or not estado or not total:
            error = 'Ticket, estado y total son obligatorios.'
        if not billing_entity_type or not billing_entity_id:
            error = 'Tipo y ID de entidad de facturación son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''INSERT INTO presupuestos (ticket_id, freelancer_id, estado, total, billing_entity_type, billing_entity_id, pdf_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (ticket_id, g.user.id, estado, total, billing_entity_type, billing_entity_id, pdf_url)
                )
                db.commit()
                flash('¡Presupuesto añadido correctamente!')
                return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('freelancer_quotes/form.html', quote=None, clients=clients, tickets=tickets, providers=providers, freelancers_list=freelancers_list)

@bp.route('/<int:quote_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_freelancer_quote(quote_id):
    db = get_db()
    quote = db.execute(
        'SELECT * FROM presupuestos WHERE id = ? AND freelancer_id = ?',
        (quote_id, g.user.id)
    ).fetchone()

    if quote is None:
        flash('Presupuesto no encontrado o no tienes permiso para editarlo.', 'error')
        return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))

    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    tickets = db.execute('SELECT id, descripcion FROM tickets ORDER BY descripcion').fetchall()
    providers = db.execute('SELECT id, nombre FROM proveedores ORDER BY nombre').fetchall()
    freelancers_list = db.execute('SELECT u.id, u.username FROM users u JOIN freelancers f ON u.id = f.user_id ORDER BY u.username').fetchall()

    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id', type=int)
        estado = request.form.get('estado')
        total = request.form.get('total', type=float)
        billing_entity_type = request.form.get('billing_entity_type')
        billing_entity_id = request.form.get('billing_entity_id', type=int)
        pdf_url = quote['pdf_url'] # Keep existing URL if no new file is uploaded

        if 'quote_file' in request.files:
            quote_file = request.files['quote_file']
            if quote_file.filename != '':
                allowed_extensions = {'pdf'}
                if '.' in quote_file.filename and \
                   quote_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(quote_file.filename)
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True) # Ensure upload folder exists
                    file_path = os.path.join(upload_folder, filename)
                    quote_file.save(file_path)
                    pdf_url = url_for('uploaded_file', filename=filename) # Store URL path
                else:
                    error = 'Tipo de archivo no permitido para el presupuesto (solo PDF).

        error = None

        if not ticket_id or not estado or not total:
            error = 'Ticket, estado y total son obligatorios.'
        if not billing_entity_type or not billing_entity_id:
            error = 'Tipo y ID de entidad de facturación son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE presupuestos SET 
                       ticket_id = ?, estado = ?, total = ?, billing_entity_type = ?, billing_entity_id = ?, pdf_url = ?
                       WHERE id = ? AND freelancer_id = ?''',
                    (ticket_id, estado, total, billing_entity_type, billing_entity_id, pdf_url, quote_id, g.user.id)
                )
                db.commit()
                flash('¡Presupuesto actualizado correctamente!')
                return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('freelancer_quotes/form.html', quote=quote, clients=clients, tickets=tickets, providers=providers, freelancers_list=freelancers_list)
