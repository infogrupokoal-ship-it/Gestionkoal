import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend.auth import login_required
from backend.db_utils import get_db
from backend.forms import MaterialForm
from backend.market_study import get_market_study_for_material  # New import

bp = Blueprint('materials', __name__, url_prefix='/materials')

@bp.route('/')
@login_required
def list_materials():
    if not current_user.has_permission('manage_materials'):
        flash('No tienes permiso para gestionar materiales.', 'error')
        return redirect(url_for('index'))
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    materials = db.execute('SELECT id, sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario FROM materiales').fetchall()
    return render_template('materials/list.html', materials=materials)

@bp.route('/<int:material_id>')
@login_required
def view_material(material_id):
    if not current_user.has_permission('manage_materials'):
        flash('No tienes permiso para ver este material.', 'error')
        return redirect(url_for('index'))
    db = get_db()
    if db is None:
        flash('Database connection error.', 'error')
        return redirect(url_for('index')) # Redirect to a safe page, e.g., index or login

    material = db.execute(
        '''
        SELECT m.*, p.nombre as proveedor_nombre
        FROM materiales m
        LEFT JOIN providers p ON m.proveedor_principal_id = p.id
        WHERE m.id = ?
        ''',
        (material_id,)
    ).fetchone()

    if material is None:
        flash('Material no encontrado.', 'error')
        return redirect(url_for('materials.list_materials'))

    return render_template('materials/view.html', material=material)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_material():
    if not current_user.has_permission('manage_materials'):
        flash('No tienes permiso para añadir materiales.', 'error')
        return redirect(url_for('materials.list_materials'))
    db = get_db()
    form = MaterialForm()
    # Populate provider choices
    providers = db.execute('SELECT id, nombre FROM providers ORDER BY nombre').fetchall()
    form.proveedor_principal_id.choices = [(p['id'], p['nombre']) for p in providers]
    form.proveedor_principal_id.choices.insert(0, ('', 'Seleccione un proveedor'))

    if form.validate_on_submit():
        sku = form.sku.data.strip()
        if not sku:
            # Auto-generate SKU if empty
            last_sku_row = db.execute(
                "SELECT sku FROM materiales WHERE sku LIKE 'MAT-%' ORDER BY sku DESC LIMIT 1"
            ).fetchone()
            if last_sku_row and last_sku_row['sku']:
                try:
                    last_num = int(last_sku_row['sku'].split('-')[1])
                    new_num = last_num + 1
                    sku = f"MAT-{new_num:04d}"
                except (IndexError, ValueError):
                    sku = "MAT-0001"
            else:
                sku = "MAT-0001"

        try:
            db.execute(
                'INSERT INTO materiales (sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario, proveedor_principal_id, comision_empresa) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (sku, form.nombre.data, form.categoria.data, form.unidad.data, form.stock.data, form.stock_min.data, form.ubicacion.data, form.costo_unitario.data, form.proveedor_principal_id.data, form.comision_empresa.data)
            )
            db.commit()
            flash(f'¡Material añadido correctamente! SKU asignado: {sku}')
            return redirect(url_for('materials.list_materials'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash(f"El material con SKU {sku} ya existe.", 'error')
        except Exception as e:
            db.rollback()
            flash(f"Ocurrió un error inesperado: {e}", 'error')

    return render_template('materials/form.html', form=form, title="Añadir Material")

@bp.route('/<int:material_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_material(material_id):
    if not current_user.has_permission('manage_materials'):
        flash('No tienes permiso para editar materiales.', 'error')
        return redirect(url_for('materials.list_materials'))
    db = get_db()
    material = db.execute('SELECT * FROM materiales WHERE id = ?', (material_id,)).fetchone()

    if material is None:
        flash('Material no encontrado.', 'error')
        return redirect(url_for('materials.list_materials'))

    form = MaterialForm(obj=material)
    # Populate provider choices
    providers = db.execute('SELECT id, nombre FROM providers ORDER BY nombre').fetchall()
    form.proveedor_principal_id.choices = [(p['id'], p['nombre']) for p in providers]
    form.proveedor_principal_id.choices.insert(0, ('', 'Seleccione un proveedor'))

    if form.validate_on_submit():
        try:
            db.execute(
                'UPDATE materiales SET sku = ?, nombre = ?, categoria = ?, unidad = ?, stock = ?, stock_min = ?, ubicacion = ?, costo_unitario = ?, proveedor_principal_id = ?, comision_empresa = ? WHERE id = ?',
                (form.sku.data, form.nombre.data, form.categoria.data, form.unidad.data, form.stock.data, form.stock_min.data, form.ubicacion.data, form.costo_unitario.data, form.proveedor_principal_id.data, form.comision_empresa.data, material_id)
            )
            db.commit()
            flash('¡Material actualizado correctamente!')
            return redirect(url_for('materials.list_materials'))
        except sqlite3.IntegrityError:
            db.rollback()
            flash(f"El material con SKU {form.sku.data} ya existe.", 'error')
        except Exception as e:
            db.rollback()
            flash(f"Ocurrió un error inesperado: {e}", 'error')

    # For GET request, set the value for the SelectField
    if request.method == 'GET':
        form.proveedor_principal_id.data = material['proveedor_principal_id']

    market_study_data = get_market_study_for_material(material_id)
    return render_template('materials/form.html', form=form, title="Editar Material", market_study_data=market_study_data)
