import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import sqlite3

from backend.db import get_db
from backend.auth import login_required

bp = Blueprint('materials', __name__, url_prefix='/materials')

@bp.route('/')
@login_required
def list_materials():
    db = get_db()
    materials = db.execute(
        'SELECT id, sku, nombre, categoria, unidad, stock, stock_min, ubicacion FROM materiales ORDER BY nombre'
    ).fetchall()
    return render_template('materials/list.html', materials=materials)

@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_material():
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
        if costo_unitario is not None and proveedor_principal_id:
            provider = db.execute('SELECT descuento_general FROM proveedores WHERE id = ?', (proveedor_principal_id,)).fetchone()
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

    db = get_db()
    providers = db.execute('SELECT id, nombre FROM proveedores ORDER BY nombre').fetchall()
    return render_template('materials/form.html', material=None, providers=providers)

@bp.route('/<int:material_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_material(material_id):
    db = get_db()
    material = db.execute('SELECT id, sku, nombre, categoria, unidad, stock, stock_min, ubicacion, costo_unitario, proveedor_principal_id, comision_empresa, precio_venta_sugerido FROM materiales WHERE id = ?', (material_id,)).fetchone()

    if material is None:
        flash('Material no encontrado.')
        return redirect(url_for('materials.list_materials'))

    if request.method == 'POST':
        sku = request.form['sku']
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        unidad = request.form['unidad']
        stock = request.form['stock']
        stock_min = request.form['stock_min']
        ubicacion = request.form['ubicacion']
        costo_unitario = request.form.get('costo_unitario', type=float, default=0.0) # Default to 0.0 if not provided
        proveedor_principal_id = request.form.get('proveedor_principal_id', type=int)
        comision_empresa = request.form.get('comision_empresa', type=float, default=0.0)

        precio_venta_sugerido = None
        
        # Fetch market study data for the material (if available)
        market_study_data = db.execute(
            "SELECT precio_recomendado FROM estudio_mercado WHERE tipo_elemento = 'material' AND elemento_id = ? ORDER BY fecha_estudio DESC LIMIT 1",
            (material_id,)
        ).fetchone()

        base_price_from_market = market_study_data['precio_recomendado'] if market_study_data else None

        if costo_unitario is not None and proveedor_principal_id:
            provider = db.execute('SELECT descuento_general FROM proveedores WHERE id = ?', (proveedor_principal_id,)).fetchone()
            if provider:
                descuento_general = provider['descuento_general'] if provider['descuento_general'] is not None else 0.0
                
                # Use market study price if available, otherwise calculate from cost_unitario
                if base_price_from_market is not None:
                    precio_venta_sugerido = base_price_from_market * (1 + comision_empresa / 100)
                else:
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

    db = get_db()
    providers = db.execute('SELECT id, nombre FROM proveedores ORDER BY nombre').fetchall()
    return render_template('materials/form.html', material=material, providers=providers)
