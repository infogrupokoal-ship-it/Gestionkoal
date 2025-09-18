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
        sku = request.form['sku']
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        unidad = request.form['unidad']
        stock = request.form['stock']
        stock_min = request.form['stock_min']
        ubicacion = request.form['ubicacion']
        db = get_db()
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
                    'INSERT INTO materiales (sku, nombre, categoria, unidad, stock, stock_min, ubicacion) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (sku, nombre, categoria, unidad, stock, stock_min, ubicacion)
                )
                db.commit()
                flash('¡Material añadido correctamente!')
                return redirect(url_for('materials.list_materials'))
            except sqlite3.IntegrityError:
                error = f"El material con SKU {sku} ya existe."
            except Exception as e:
                error = f"Ocurrió un error inesperado: {e}"
            
            if error:
                flash(error)

    return render_template('materials/form.html')

@bp.route('/<int:material_id>/edit', methods=('GET', 'POST'))
@login_required
def edit_material(material_id):
    db = get_db()
    material = db.execute('SELECT id, sku, nombre, categoria, unidad, stock, stock_min, ubicacion FROM materiales WHERE id = ?', (material_id,)).fetchone()

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
                    'UPDATE materiales SET sku = ?, nombre = ?, categoria = ?, unidad = ?, stock = ?, stock_min = ?, ubicacion = ? WHERE id = ?',
                    (sku, nombre, categoria, unidad, stock, stock_min, ubicacion, material_id)
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

    return render_template('materials/form.html', material=material)
