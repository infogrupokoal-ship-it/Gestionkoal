import functools
import secrets
from datetime import datetime, timedelta
import os

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
import sqlite3
from backend.db import get_db
from backend.auth import login_required
from backend.wa_client import send_whatsapp_text # For sending signed PDF via WhatsApp
from backend.receipt_generator import generate_receipt_pdf # For generating signed PDF

bp = Blueprint('quotes', __name__, url_prefix='/quotes')

@bp.route('/trabajos/<int:trabajo_id>/add', methods=('GET', 'POST'))
@login_required
def add_quote(trabajo_id):
    db = get_db()
    trabajo = db.execute('SELECT * FROM tickets WHERE id = ?', (trabajo_id,)).fetchone()

    if trabajo is None:
        flash('El trabajo no existe.')
        return redirect(url_for('jobs.list_jobs'))

    if request.method == 'POST':
        estado = request.form.get('estado')
        total = 0.0
        items_data = []
        error = None

        descripciones = request.form.getlist('item_descripcion[]')
        quantities = request.form.getlist('item_qty[]')
        unit_prices = request.form.getlist('item_precio_unit[]')

        # Recopilar y validar ítems
        for i in range(len(descripciones)):
            descripcion = descripciones[i].strip()
            qty_str = quantities[i].strip()
            precio_unit_str = unit_prices[i].strip()

            if not descripcion and (not qty_str or not precio_unit_str):
                continue # Ignorar líneas completamente vacías

            try:
                qty = float(qty_str) if qty_str else 0.0
                precio_unit = float(precio_unit_str) if precio_unit_str else 0.0
            except ValueError:
                error = 'Cantidad y Precio Unitario deben ser números válidos.'
                break
            
            if not descripcion:
                error = 'La descripción del ítem no puede estar vacía si hay cantidad o precio.'
                break

            item_total = qty * precio_unit
            total += item_total
            items_data.append({
                'descripcion': descripcion,
                'qty': qty,
                'precio_unit': precio_unit
            })
        
        if error is not None:
            flash(error)
        elif not items_data:
            flash('Debe añadir al menos un ítem al presupuesto.')
        else:
            try:
                # Insertar Presupuesto principal
                cursor = db.execute(
                    'INSERT INTO presupuestos (ticket_id, estado, total) VALUES (?, ?, ?)',
                    (trabajo_id, estado, total)
                )
                presupuesto_id = cursor.lastrowid

                # Insertar ítems del Presupuesto
                for item in items_data:
                    db.execute(
                        'INSERT INTO presupuesto_items (presupuesto_id, descripcion, qty, precio_unit) VALUES (?, ?, ?, ?)',
                        (presupuesto_id, item['descripcion'], item['qty'], item['precio_unit'])
                    )
                
                db.commit()
                flash('¡Presupuesto creado correctamente!')
                return redirect(url_for('jobs.edit_job', job_id=trabajo_id)) # Redirigir de vuelta al trabajo

            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error al guardar el presupuesto: {e}"
                flash(error)

    return render_template('quotes/form.html', trabajo=trabajo, presupuesto=None)

@bp.route('/<int:quote_id>/view', methods=('GET', 'POST'))
@login_required
def view_quote(quote_id):
    db = get_db()
    presupuesto = db.execute('SELECT * FROM presupuestos WHERE id = ?', (quote_id,)).fetchone()

    if presupuesto is None:
        flash('Presupuesto no encontrado.')
        return redirect(url_for('jobs.list_jobs')) # Redirigir a la lista de trabajos o a una lista de presupuestos

    # Fetch items for the quote
    items = db.execute(
        'SELECT id, descripcion, qty, precio_unit FROM presupuesto_items WHERE presupuesto_id = ?',
        (quote_id,)
    ).fetchall()

    if request.method == 'POST':
        estado = request.form.get('estado')
        total = 0.0
        items_to_process = []
        error = None

        item_ids = request.form.getlist('item_id[]')
        descripciones = request.form.getlist('item_descripcion[]')
        quantities = request.form.getlist('item_qty[]')
        unit_prices = request.form.getlist('item_precio_unit[]')

        # Recopilar y validar ítems
        for i in range(len(descripciones)):
            item_id_str = item_ids[i].strip()
            descripcion = descripciones[i].strip()
            qty_str = quantities[i].strip()
            precio_unit_str = unit_prices[i].strip()

            # Si la descripción está vacía y no hay ID, es una fila vacía que ignoramos
            if not descripcion and not item_id_str and (not qty_str or not precio_unit_str):
                continue

            try:
                qty = float(qty_str) if qty_str else 0.0
                precio_unit = float(precio_unit_str) if precio_unit_str else 0.0
            except ValueError:
                error = 'Cantidad y Precio Unitario deben ser números válidos.'
                break
            
            if not descripcion:
                error = 'La descripción del ítem no puede estar vacía si hay cantidad o precio.'
                break

            item_total = qty * precio_unit
            total += item_total
            items_to_process.append({
                'id': int(item_id_str) if item_id_str else None,
                'descripcion': descripcion,
                'qty': qty,
                'precio_unit': precio_unit
            })
        
        if error is not None:
            flash(error)
        elif not items_to_process:
            flash('Debe añadir al menos un ítem al presupuesto.')
        else:
            try:
                # Actualizar Presupuesto principal
                db.execute(
                    'UPDATE presupuestos SET estado = ?, total = ? WHERE id = ?',
                    (estado, total, quote_id)
                )

                # Obtener IDs de ítems existentes para detectar eliminaciones
                existing_item_ids = [item['id'] for item in items if item['id'] is not None]
                submitted_item_ids = [item['id'] for item in items_to_process if item['id'] is not None]

                # Eliminar ítems que ya no están en el formulario
                for existing_id in existing_item_ids:
                    if existing_id not in submitted_item_ids:
                        db.execute('DELETE FROM presupuesto_items WHERE id = ?', (existing_id,))

                # Actualizar/Insertar ítems
                for item in items_to_process:
                    if item['id']:
                        # Actualizar ítem existente
                        db.execute(
                            'UPDATE presupuesto_items SET descripcion = ?, qty = ?, precio_unit = ? WHERE id = ?',
                            (item['descripcion'], item['qty'], item['precio_unit'], item['id'])
                        )
                    else:
                        # Insertar nuevo ítem
                        db.execute(
                            'INSERT INTO presupuesto_items (presupuesto_id, descripcion, qty, precio_unit) VALUES (?, ?, ?, ?)',
                            (quote_id, item['descripcion'], item['qty'], item['precio_unit'])
                        )
                
                db.commit()
                flash('¡Presupuesto actualizado correctamente!')
                return redirect(url_for('quotes.view_quote', quote_id=quote_id))

            except Exception as e:
                db.rollback()
                error = f"Ocurrió un error al actualizar el presupuesto: {e}"
                flash(error)

    return render_template('quotes/view.html', presupuesto=presupuesto, items=items)

@bp.route('/<int:quote_id>/delete', methods=('POST',))
@login_required
def delete_quote(quote_id):
    db = get_db()
    presupuesto = db.execute('SELECT id FROM presupuestos WHERE id = ?', (quote_id,)).fetchone()

    if presupuesto is None:
        flash('Presupuesto no encontrado.')
        return redirect(url_for('jobs.list_jobs')) # O a la lista de presupuestos

    try:
        # Eliminar ítems del presupuesto
        db.execute('DELETE FROM presupuesto_items WHERE presupuesto_id = ?', (quote_id,))
        # Eliminar el presupuesto principal
        db.execute('DELETE FROM presupuestos WHERE id = ?', (quote_id,))
        db.commit()
        flash('¡Presupuesto eliminado correctamente!')
    except Exception as e:
        db.rollback()
        flash(f'Ocurrió un error al eliminar el presupuesto: {e}')
    
    return redirect(url_for('jobs.list_jobs')) # Redirigir a la lista de trabajos

@bp.route('/send_for_signature/<int:quote_id>', methods=('POST',))
@login_required
def send_quote_for_signature(quote_id):
    db = get_db()
    quote = db.execute(
        'SELECT p.id, p.ticket_id, p.total, t.cliente_id, cl.whatsapp_number, cl.nombre as client_name
         FROM presupuestos p
         JOIN tickets t ON p.ticket_id = t.id
         JOIN clientes cl ON t.cliente_id = cl.id
         WHERE p.id = ?',
        (quote_id,)
    ).fetchone()

    if quote is None:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(request.referrer or url_for('index'))

    if not quote['whatsapp_number']:
        flash('El cliente no tiene un número de WhatsApp registrado.', 'error')
        return redirect(request.referrer or url_for('index'))

    try:
        # Generate a secure, time-limited token
        signature_token = secrets.token_urlsafe(32)
        # Store token and expiry in DB (e.g., 24 hours validity)
        token_expires = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')

        db.execute(
            'UPDATE presupuestos SET signature_token = ?, token_expires = ? WHERE id = ?',
            (signature_token, token_expires, quote_id)
        )
        db.commit()

        # Construct the public signature URL
        signature_url = url_for('quotes.client_sign_quote', token=signature_token, _external=True)

        # Send via WhatsApp
        message = f"¡Hola {quote['client_name']}! Tienes un presupuesto pendiente de firma para el trabajo {quote['ticket_id']}. Por favor, fírmalo aquí: {signature_url}"
        send_whatsapp_text(quote['whatsapp_number'], message)

        flash('Enlace de firma enviado al cliente por WhatsApp.', 'success')
    except Exception as e:
        flash(f'Error al enviar el enlace de firma: {e}', 'error')
        db.rollback()

    return redirect(request.referrer or url_for('index'))

@bp.route('/sign/<string:token>', methods=('GET', 'POST'))
def client_sign_quote(token):
    db = get_db()
    # Find the quote by token
    quote = db.execute(
        'SELECT p.*, c.nombre as client_name, cl.whatsapp_number FROM presupuestos p JOIN tickets t ON p.ticket_id = t.id JOIN clientes cl ON t.cliente_id = cl.id WHERE p.signature_token = ?',
        (token,)
    ).fetchone()

    if quote is None:
        flash('Enlace de firma no válido o caducado.', 'error')
        return redirect(url_for('auth.login')) # Or a generic error page

    # Check if already signed
    if quote['client_signature_data']:
        flash('Este presupuesto ya ha sido firmado.', 'info')
        return render_template('quotes/client_sign_quote.html', quote=quote, signed=True)

    # Fetch items for the quote
    items = db.execute(
        'SELECT descripcion, qty, precio_unit FROM presupuesto_items WHERE presupuesto_id = ?',
        (quote['id'],)
    ).fetchall()

    if request.method == 'POST':
        client_name = request.form.get('client_name')
        signature_data = request.form.get('signature_data')

        if not client_name or not signature_data:
            flash('Por favor, introduce tu nombre y firma el documento.', 'error')
            return render_template('quotes/client_sign_quote.html', quote=quote, items=items, token=token)

        try:
            # Update quote with signature data
            db.execute(
                'UPDATE presupuestos SET client_signature_data = ?, client_signature_date = ?, client_signed_by = ?, estado = ? WHERE id = ?',
                (signature_data, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), client_name, 'Aprobado', quote['id'])
            )
            db.commit()

            # --- Generate Signed PDF ---
            # For simplicity, let's assume generate_receipt_pdf can handle quote data
            # and embed signature. This will need a proper PDF generation library.
            # For now, we'll mock the PDF generation and store a placeholder URL.
            pdf_filename = f"presupuesto_firmado_{quote['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            pdf_filepath = os.path.join(upload_folder, pdf_filename)

            # Mock PDF generation (replace with actual PDF library call)
            # generate_receipt_pdf(output_path=pdf_filepath, quote_details=quote, items=items, signature_data=signature_data)
            with open(pdf_filepath, 'w') as f:
                f.write(f"Presupuesto {quote['id']} firmado por {client_name} el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total: {quote['total']} EUR\n")
                f.write("Firma: (ver imagen adjunta o datos de firma)")

            signed_pdf_url = url_for('uploaded_file', filename=pdf_filename, _external=True)
            db.execute('UPDATE presupuestos SET signed_pdf_url = ? WHERE id = ?', (signed_pdf_url, quote['id']))
            db.commit()

            # --- Send Signed PDF via WhatsApp ---
            if quote['whatsapp_number']:
                whatsapp_message = f"¡Hola {quote['client_name']}! Tu presupuesto {quote['id']} ha sido firmado y aprobado. Puedes verlo aquí: {signed_pdf_url}"
                send_whatsapp_text(quote['whatsapp_number'], whatsapp_message)
                flash('Presupuesto firmado y enviado por WhatsApp.', 'success')
            else:
                flash('Presupuesto firmado. No se pudo enviar por WhatsApp (número no disponible).', 'warning')

            flash('Presupuesto firmado y aprobado correctamente.', 'success')
            return redirect(url_for('quotes.client_sign_quote', token=token, signed=True))

        except Exception as e:
            db.rollback()
            flash(f'Ocurrió un error al procesar la firma: {e}', 'error')

    return render_template('quotes/client_sign_quote.html', quote=quote, items=items, token=token)
