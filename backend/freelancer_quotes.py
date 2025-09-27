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
           FROM presupuestos p 
           JOIN tickets t ON p.ticket_id = t.id
           JOIN clientes c ON t.cliente_id = c.id
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
        error = None
        uploaded_files_info = []
        
        # 1. Handle file uploads first
        quote_files = request.files.getlist('quote_files')
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        for file in quote_files:
            if file and file.filename != '':
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(file.filename)
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    uploaded_files_info.append({
                        'url': url_for('uploaded_file', filename=filename),
                        'tipo': file.mimetype
                    })
                else:
                    error = 'Tipo de archivo no permitido. Solo se aceptan PDF, JPG, PNG.'
                    break # Stop processing on first invalid file
        
        # 2. Process the rest of the form
        ticket_id = request.form.get('ticket_id', type=int)
        estado = request.form.get('estado')
        total = request.form.get('total', type=float)
        billing_entity_type = request.form.get('billing_entity_type')
        billing_entity_id = request.form.get('billing_entity_id', type=int)

        if not ticket_id or not estado or not total:
            error = 'Ticket, estado y total son obligatorios.'
        if not billing_entity_type or not billing_entity_id:
            error = 'Tipo y ID de entidad de facturación son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                # 3. Insert into DB
                # The 'pdf_url' column is now deprecated for this form
                cursor = db.execute(
                    '''INSERT INTO presupuestos (ticket_id, freelancer_id, estado, total, billing_entity_type, billing_entity_id)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (ticket_id, g.user.id, estado, total, billing_entity_type, billing_entity_id)
                )
                presupuesto_id = cursor.lastrowid

                # 4. Link uploaded files to the new quote
                for file_info in uploaded_files_info:
                    db.execute(
                        'INSERT INTO ficheros (presupuesto_id, url, tipo) VALUES (?, ?, ?)',
                        (presupuesto_id, file_info['url'], file_info['tipo'])
                    )

                db.commit()
                flash('¡Presupuesto añadido correctamente con {} archivos!'.format(len(uploaded_files_info)))
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

    # Fetch existing files for this quote
    existing_files = db.execute(
        'SELECT id, url, tipo FROM ficheros WHERE presupuesto_id = ?', (quote_id,)
    ).fetchall()

    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    tickets = db.execute('SELECT id, descripcion FROM tickets ORDER BY descripcion').fetchall()
    providers = db.execute('SELECT id, nombre FROM proveedores ORDER BY nombre').fetchall()
    freelancers_list = db.execute('SELECT u.id, u.username FROM users u JOIN freelancers f ON u.id = f.user_id ORDER BY u.username').fetchall()

    if request.method == 'POST':
        error = None
        
        # 1. Handle new file uploads
        quote_files = request.files.getlist('quote_files')
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg'}
        for file in quote_files:
            if file and file.filename != '':
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(file.filename)
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    # Insert new file record into DB
                    db.execute(
                        'INSERT INTO ficheros (presupuesto_id, url, tipo) VALUES (?, ?, ?)',
                        (quote_id, url_for('uploaded_file', filename=filename), file.mimetype)
                    )
                else:
                    error = 'Tipo de archivo no permitido. Solo se aceptan PDF, JPG, PNG.'
                    break
        
        # 2. Process the rest of the form
        ticket_id = request.form.get('ticket_id', type=int)
        estado = request.form.get('estado')
        total = request.form.get('total', type=float)
        billing_entity_type = request.form.get('billing_entity_type')
        billing_entity_id = request.form.get('billing_entity_id', type=int)

        if not ticket_id or not estado or not total:
            error = 'Ticket, estado y total son obligatorios.'
        if not billing_entity_type or not billing_entity_id:
            error = 'Tipo y ID de entidad de facturación son obligatorios.'

        if error is not None:
            flash(error)
        else:
            try:
                # 3. Update the main quote object (removing obsolete pdf_url)
                db.execute(
                    '''UPDATE presupuestos SET 
                       ticket_id = ?, estado = ?, total = ?, billing_entity_type = ?, billing_entity_id = ?
                       WHERE id = ? AND freelancer_id = ?''',
                    (ticket_id, estado, total, billing_entity_type, billing_entity_id, quote_id, g.user.id)
                )
                db.commit()
                flash('¡Presupuesto actualizado correctamente!')
                return redirect(url_for('freelancer_quotes.edit_freelancer_quote', quote_id=quote_id))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    return render_template('freelancer_quotes/form.html', quote=quote, clients=clients, tickets=tickets, providers=providers, freelancers_list=freelancers_list)

@bp.route('/files/<int:file_id>/delete', methods=('POST',))
@login_required
def delete_file(file_id):
    db = get_db()
    # First, get the file to find which quote it belongs to, ensuring ownership
    file = db.execute(
        '''SELECT f.id, p.id as quote_id FROM ficheros f 
           JOIN presupuestos p ON f.presupuesto_id = p.id
           WHERE f.id = ? AND p.freelancer_id = ?''', (file_id, g.user.id)
    ).fetchone()

    if file:
        # TODO: Also delete the actual file from the /uploads folder
        db.execute('DELETE FROM ficheros WHERE id = ?', (file_id,))
        db.commit()
        flash('Archivo eliminado.', 'success')
        return redirect(url_for('freelancer_quotes.edit_freelancer_quote', quote_id=file['quote_id']))
    else:
        flash('Archivo no encontrado o no tienes permiso para eliminarlo.', 'error')
        return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
