import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required
from backend.market_study import get_market_study_for_material # New import

bp = Blueprint('materials', __name__, url_prefix='/materials')

@bp.route('/')
@login_required
def list_materials():
    db = get_db()
    materials = db.execute(
        'SELECT id, sku, nombre, categoria, unidad, stock, stock_min, ubicacion, precio_venta_sugerido FROM materiales ORDER BY nombre'
    ).fetchall()
    return render_template('materials/list.html', materials=materials)

@bp.route('/<int:material_id>')
@login_required
def view_material(material_id):
    db = get_db()
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
    db = get_db()
    market_study_data = None # Initialize for GET request

    if request.method == 'POST':
        sku = request.form.get('sku', '').strip()
        nombre = request.form.get('nombre')
        categoria = request.form.get('categoria')
        unidad = request.form.get('unidad')
        stock = request.form.get('stock')
        stock_min = request.form.get('stock_min')
        ubicacion = request.form.get('ubicacion')
        costo_unitario = request.form.get('costo_unitario', type=float, default=0.0) # Default to 0.0 if not provided
        proveedor_principal_id = request.form.get('proveedor_principal_id', type=int)
        comision_empresa = request.form.get('comision_empresa', type=float, default=0.0)
        
        precio_venta_sugerido = None
        
        # For simplicity, let's just pass market_study_data as None for 'add' initially,
        # and focus on 'edit' where material_id is known.
        # The user can manually check market study for new materials.

        if costo_unitario is not None and proveedor_principal_id:
            provider = db.execute('SELECT descuento_general FROM providers WHERE id = ?', (proveedor_principal_id,)).fetchone() # Corrected table name
            if provider:
                descuento_general = provider['descuento_general'] if provider['descuento_general'] is not None else 0.0
                precio_venta_sugerido = costo_unitario * (1 - descuento_general / 100) * (1 + comision_empresa / 100)

        error = None

        if not nombre:
            error = 'El nombre es obligatorio.'

        if not sku:
            last_sku_row = db.execute(
                "SELECT sku FROM materiales WHERE sku LIKE 'MAT-%' ORDER BY sku DESC LIMIT 1"
            ).fetchone()
            if last_sku_row and last_sku_row['sku']:
                last_sku = last_sku_row['sku']
                try:
                    last_num = int(last_sku.split('-')[1])
                    new_num = last_num + 1
                    sku = f"MAT-{new_num:04d}"
                except (IndexError, ValueError):
                    # Fallback if parsing fails
                    sku = f"MAT-0001"
            else:
                sku = "MAT-0001"

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'INSERT INTO materiales (sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario, proveedor_principal_id, comision_empresa, precio_venta_sugerido) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario, proveedor_principal_id, comision_empresa, precio_venta_sugerido)
                )
                db.commit()
                flash(f'¡Material añadido correctamente! SKU asignado: {sku}')
                return redirect(url_for('materials.list_materials'))
            except sqlite3.IntegrityError:
                error = f"El material con SKU {sku} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    providers = db.execute('SELECT id, nombre FROM providers ORDER BY nombre').fetchall() # Corrected table name
    return render_template('materials/form.html', material=None, providers=providers, market_study_data=market_study_data) # Pass market_study_data

@bp.route('/<int:material_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_material(material_id):
    db = get_db()
    material = db.execute('SELECT id, sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario, proveedor_principal_id, comision_empresa, precio_venta_sugerido FROM materiales WHERE id = ?', (material_id,)).fetchone()

    if material is None:
        flash('Material no encontrado.')
        return redirect(url_for('materials.list_materials'))

    market_study_data = get_market_study_for_material(material_id) # Fetch market study data

    if request.method == 'POST':
        sku = request.form.get('sku')
        nombre = request.form.get('nombre')
        categoria = request.form.get('categoria')
        unidad = request.form.get('unidad')
        stock = request.form.get('stock')
        stock_min = request.form.get('stock_min')
        ubicacion = request.form.get('ubicacion')
        costo_unitario = request.form.get('costo_unitario', type=float, default=0.0) # Default to 0.0 if not provided
        proveedor_principal_id = request.form.get('proveedor_principal_id', type=int)
        comision_empresa = request.form.get('comision_empresa', type=float, default=0.0)

        precio_venta_sugerido = None
        
        # Use market study data for suggested price if available
        if market_study_data and market_study_data['price_avg'] is not None:
            base_price_from_market = market_study_data['price_avg']
            precio_venta_sugerido = base_price_from_market * (1 + comision_empresa / 100)
        elif costo_unitario is not None and proveedor_principal_id:
            provider = db.execute('SELECT descuento_general FROM providers WHERE id = ?', (proveedor_principal_id,)).fetchone() # Corrected table name
            if provider:
                descuento_general = provider['descuento_general'] if provider['descuento_general'] is not None else 0.0
                precio_venta_sugerido = costo_unitario * (1 - descuento_general / 100) * (1 + comision_empresa / 100)

        error = None

        if not sku:
            error = 'El SKU es obligatorio.'
        elif not nombre:
            error = 'El nombre es obligatorio.'

        if error is not None:
            flash(error)
        else:
            try:
                db.execute(
                    'UPDATE materiales SET sku = ?, nombre = ?, categoria = ?, unidad = ?, stock = ?, stock_min = ?, ubicacion = ?, costo_unitario = ?, proveedor_principal_id = ?, comision_empresa = ?, precio_venta_sugerido = ? WHERE id = ?',
                    (sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario, proveedor_principal_id, comision_empresa, precio_venta_sugerido, material_id)
                )
                db.commit()
                flash('¡Material actualizado correctamente!')
                return redirect(url_for('materials.list_materials'))
            except sqlite3.IntegrityError:
                error = f"El material con SKU {sku} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    providers = db.execute('SELECT id, nombre FROM providers ORDER BY nombre').fetchall() # Corrected table name
    return render_template('materials/form.html', material=material, providers=providers, market_study_data=market_study_data)
