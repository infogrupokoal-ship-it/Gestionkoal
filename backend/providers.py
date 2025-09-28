import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3
from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('providers', __name__, url_prefix='/proveedores')

@bp.route('/')
@login_required
def list_providers():
    db = get_db()
    providers = db.execute(
        'SELECT id, nombre, telefono, email FROM proveedores ORDER BY nombre'
    ).fetchall()
    return render_template('proveedores/list.html', providers=providers)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_provider():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        tipo_proveedor = request.form.get('tipo_proveedor') # FIX: Added this line to get the provider type from the form
        descuento_general = request.form.get('descuento_general', type=float, default=0.0)
        condiciones_especiales = request.form.get('condiciones_especiales')
        db = get_db()
        error = None

        if not nombre:
            error = 'El nombre es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'INSERT INTO proveedores (nombre, telefono, email, tipo_proveedor, descuento_general, condiciones_especiales) VALUES (?, ?, ?, ?, ?, ?)',
                    (nombre, telefono, email, tipo_proveedor, descuento_general, condiciones_especiales)
                )
                db.commit()
                flash('¡Proveedor añadido correctamente!')

                # --- Notification Logic ---
                from .notifications import add_notification
                # Get admin user IDs
                admin_users = db.execute('SELECT u.id FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.code = ?', ('admin',)).fetchall()

                # Prepare notification message
                notification_message = (
                    f"Nuevo proveedor añadido por {g.user.username}: {nombre} ({tipo_proveedor})."
                )

                # Notify creator
                add_notification(db, g.user.id, notification_message)

                # Notify admins
                for admin in admin_users:
                    if admin['id'] != g.user.id: # Avoid double notification for creator if they are admin
                        add_notification(db, admin['id'], notification_message)
                # --- End Notification Logic ---
                return redirect(url_for('providers.list_providers'))
            except sqlite3.IntegrityError:
                error = f"El proveedor {nombre} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('proveedores/form.html', proveedor=None)

@bp.route('/<int:provider_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_provider(provider_id):
    db = get_db()
    proveedor = db.execute('SELECT id, nombre, telefono, email, tipo_proveedor, contacto_persona, direccion, cif, web, notas, condiciones_pago, descuento_general, condiciones_especiales FROM proveedores WHERE id = ?', (provider_id,)).fetchone()

    if proveedor is None:
        flash('Proveedor no encontrado.')
        return redirect(url_for('providers.list_providers'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        tipo_proveedor = request.form.get('tipo_proveedor')
        contacto_persona = request.form.get('contacto_persona')
        direccion = request.form.get('direccion')
        cif = request.form.get('cif')
        web = request.form.get('web')
        notas = request.form.get('notas')
        condiciones_pago = request.form.get('condiciones_pago')
        descuento_general = request.form.get('descuento_general', type=float, default=0.0)
        condiciones_especiales = request.form.get('condiciones_especiales')
        error = None

        if not nombre:
            error = 'El nombre es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    '''UPDATE proveedores SET 
                       nombre = ?, telefono = ?, email = ?, tipo_proveedor = ?, contacto_persona = ?, 
                       direccion = ?, cif = ?, web = ?, notas = ?, condiciones_pago = ?, 
                       descuento_general = ?, condiciones_especiales = ?
                       WHERE id = ?''',
                    (nombre, telefono, email, tipo_proveedor, contacto_persona, direccion, cif, web, notas, condiciones_pago, descuento_general, condiciones_especiales, provider_id)
                )
                db.commit()
                flash('¡Proveedor actualizado correctamente!')
                return redirect(url_for('providers.list_providers'))
            except sqlite3.IntegrityError:
                error = f"El proveedor {nombre} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('proveedores/form.html', proveedor=proveedor)