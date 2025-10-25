from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend.auth import login_required
from backend.db_utils import get_db
from backend.forms import ProviderForm

bp = Blueprint('providers', __name__, url_prefix='/proveedores')

@bp.route('/')
@login_required
def list_providers():
    if not current_user.has_permission('manage_providers'):
        flash('No tienes permiso para gestionar proveedores.', 'error')
        return redirect(url_for('index'))
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    providers = db.execute('SELECT id, nombre, telefono, email, tipo_proveedor FROM providers').fetchall()
    return render_template('proveedores/list.html', providers=providers)

@bp.route('/<int:provider_id>')
@login_required
def view_provider(provider_id):
    if not current_user.has_permission('manage_providers'):
        flash('No tienes permiso para ver este proveedor.', 'error')
        return redirect(url_for('index'))
    db = get_db()
    proveedor = db.execute(
        'SELECT * FROM proveedores WHERE id = ?',
        (provider_id,)
    ).fetchone()

    if proveedor is None:
        flash('Proveedor no encontrado.', 'error')
        return redirect(url_for('providers.list_providers'))

    return render_template('proveedores/view.html', proveedor=proveedor)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_provider():
    if not current_user.has_permission('manage_providers'):
        flash('No tienes permiso para añadir proveedores.', 'error')
        return redirect(url_for('providers.list_providers'))
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('providers.list_providers'))

    form = ProviderForm()
    if form.validate_on_submit():
        try:
            db.execute(
                "INSERT INTO providers (nombre, telefono, email, tipo_proveedor) VALUES (?, ?, ?, ?)",
                (form.nombre.data, form.telefono.data, form.email.data, form.tipo_proveedor.data),
            )
            db.commit()
            flash('Provider added successfully.', 'success')
            return redirect(url_for('providers.list_providers'))
        except db.IntegrityError:
            db.rollback()
            flash(f"Provider {form.nombre.data} already exists.", 'error')
        except Exception as e:
            db.rollback()
            flash(f"An error occurred: {e}", 'error')

    return render_template('proveedores/form.html', form=form, title='Añadir Proveedor')

@bp.route('/<int:provider_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_provider(provider_id):
    if not current_user.has_permission('manage_providers'):
        flash('No tienes permiso para editar proveedores.', 'error')
        return redirect(url_for('providers.list_providers'))
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('providers.list_providers'))

    provider = db.execute(
        'SELECT id, nombre, telefono, email, tipo_proveedor FROM providers WHERE id = ?',
        (provider_id,)
    ).fetchone()

    if provider is None:
        flash('Provider not found.', 'error')
        return redirect(url_for('providers.list_providers'))

    form = ProviderForm(obj=provider)

    if form.validate_on_submit():
        try:
            db.execute(
                "UPDATE providers SET nombre = ?, telefono = ?, email = ?, tipo_proveedor = ? WHERE id = ?",
                (form.nombre.data, form.telefono.data, form.email.data, form.tipo_proveedor.data, provider_id),
            )
            db.commit()
            flash('Provider updated successfully.', 'success')
            return redirect(url_for('providers.list_providers'))
        except db.IntegrityError:
            db.rollback()
            flash(f"Provider {form.nombre.data} already exists.", 'error')
        except Exception as e:
            db.rollback()
            flash(f"An error occurred: {e}", 'error')

    return render_template('proveedores/form.html', form=form, provider=provider, title='Editar Proveedor')

@bp.route('/<int:provider_id>/delete', methods=('POST',))
@login_required
def delete_provider(provider_id):
    if not current_user.has_permission('manage_providers'):
        flash('No tienes permiso para eliminar proveedores.', 'error')
        return redirect(url_for('providers.list_providers'))
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('providers.list_providers'))

    try:
        # Check for dependencies in 'materiales' table
        linked_materials = db.execute(
            'SELECT COUNT(id) FROM materiales WHERE proveedor_principal_id = ?',
            (provider_id,)
        ).fetchone()[0]

        if linked_materials > 0:
            flash(f'No se puede eliminar el proveedor porque está asignado como principal a {linked_materials} material(es).', 'error')
            return redirect(url_for('providers.list_providers'))

        db.execute('DELETE FROM providers WHERE id = ?', (provider_id,))
        db.commit()
        flash('Provider deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting provider: {e}', 'error')
        db.rollback()

    return redirect(url_for('providers.list_providers'))
