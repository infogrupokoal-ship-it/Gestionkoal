import os

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from backend.auth import login_required
from backend.db_utils import get_db

bp = Blueprint('freelancer_quotes', __name__, url_prefix='/freelancer_quotes')

@bp.route('/')
@login_required
def list_freelancer_quotes():
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

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
@bp.route('/add/<int:job_id>', methods=('GET', 'POST'))
@login_required
def add_freelancer_quote(job_id=None):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
    clients = db.execute('SELECT id, nombre FROM clientes ORDER BY nombre').fetchall()
    tickets = db.execute('SELECT id, descripcion FROM tickets ORDER BY descripcion').fetchall()
    providers = db.execute('SELECT id, nombre FROM proveedores ORDER BY nombre').fetchall()
    freelancers_list = db.execute('SELECT u.id, u.username FROM users u JOIN freelancers f ON u.id = f.user_id ORDER BY u.username').fetchall()

    if request.method == 'POST':
        error = None
        uploaded_files_info = []

        # --- FIX: Read form variables before using them ---
        ticket_id = request.form.get('ticket_id', type=int)
        estado = request.form.get('estado')
        total = request.form.get('total', type=float)
        billing_entity_type = request.form.get('billing_entity_type')
        billing_entity_id = request.form.get('billing_entity_id', type=int)
        # --- END FIX ---

        # 1. Handle file uploads first
        quote_files = request.files.getlist('quote_files')
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip'}
        for file in quote_files:
            if file and file.filename != '':
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    filename = secure_filename(file.filename)
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    os.makedirs(upload_folder, exist_ok=True)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    # --- FIX: Populate uploaded_files_info ---
                    uploaded_files_info.append({
                        'url': url_for('uploaded_file', filename=filename),
                        'tipo': file.mimetype
                    })
                    # --- END FIX ---
                else:
                    error = f'Tipo de archivo no permitido: {file.filename}'
                    break

        if error: # Check for file upload errors
            pass
        elif not ticket_id or not estado or not total:
            error = 'Ticket, estado y total son obligatorios.'
        elif not billing_entity_type or not billing_entity_id:
            error = 'Tipo y ID de entidad de facturación son obligatorios.'
        else:
            # Validate billing_entity_id based on billing_entity_type
            if billing_entity_type == 'Cliente':
                entity = db.execute('SELECT id FROM clientes WHERE id = ?', (billing_entity_id,)).fetchone()
                if entity is None:
                    error = 'ID de Cliente no válido.'
            elif billing_entity_type == 'Proveedor':
                entity = db.execute('SELECT id FROM providers WHERE id = ?', (billing_entity_id,)).fetchone()
                if entity is None:
                    error = 'ID de Proveedor no válido.'
            else:
                error = 'Tipo de entidad de facturación no válido.'

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
                flash(f'¡Presupuesto añadido correctamente con {len(uploaded_files_info)} archivos!')
                return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
            except Exception as e:
                flash(f'Ocurrió un error inesperado: {e}', 'error')
                db.rollback()

    # For GET request or if POST fails
    quote_data = {'ticket_id': job_id} if job_id else {}
    return render_template('freelancer_quotes/form.html', quote=quote_data, clients=clients, tickets=tickets, providers=providers, freelancers_list=freelancers_list)

@bp.route('/<int:quote_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_freelancer_quote(quote_id):
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
    quote = db.execute(
        'SELECT * FROM presupuestos WHERE id = ? AND freelancer_id = ?',
        (quote_id, g.user.id)
    ).fetchone()

    if quote is None:
        flash('Presupuesto no encontrado o no tienes permiso para editarlo.', 'error')
        return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))

    # Fetch existing files for this quote
    # existing_files = db.execute(
    #     'SELECT id, url, tipo FROM ficheros WHERE presupuesto_id = ?', (quote_id,)
    # ).fetchall() # Removed unused variable

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
        else:
            # Validate billing_entity_id based on billing_entity_type
            if billing_entity_type == 'Cliente':
                entity = db.execute('SELECT id FROM clientes WHERE id = ?', (billing_entity_id,)).fetchone()
                if entity is None:
                    error = 'ID de Cliente no válido.'
            elif billing_entity_type == 'Proveedor':
                entity = db.execute('SELECT id FROM providers WHERE id = ?', (billing_entity_id,)).fetchone()
                if entity is None:
                    error = 'ID de Proveedor no válido.'
            else:
                error = 'Tipo de entidad de facturación no válido.'

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
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))

    # First, get the file to find which quote it belongs to, ensuring ownership
    file = db.execute(
        '''SELECT f.id, p.id as quote_id FROM ficheros f
           JOIN presupuestos p ON f.presupuesto_id = p.id
           WHERE f.id = ? AND p.freelancer_id = ?''', (file_id, g.user.id)
    ).fetchone()

    if file:
        try:
            # Get the full path to the file
            upload_folder = current_app.config['UPLOAD_FOLDER']
            filename = file['url'].split('/')[-1] # Extract filename from URL
            file_path = os.path.join(upload_folder, filename)

            # Delete physical file if it exists
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    current_app.logger.info(f"Physical file {file_path} deleted.")
                except OSError as e:
                    current_app.logger.error(f"Error deleting physical file {file_path}: {e}")
                    flash(f'Error al eliminar el archivo físico: {e}', 'error')

            db.execute('DELETE FROM ficheros WHERE id = ?', (file_id,))
            db.commit()
            flash('Archivo eliminado.', 'success')
            return redirect(url_for('freelancer_quotes.edit_freelancer_quote', quote_id=file['quote_id']))
        except Exception as e:
            flash(f'Error deleting file: {e}', 'error')
            db.rollback()
    else:
        flash('Archivo no encontrado o no tienes permiso para eliminarlo.', 'error')
        return redirect(url_for('freelancer_quotes.list_freelancer_quotes'))
