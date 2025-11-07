
from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.db_utils import get_db

reorder_bp = Blueprint('reorder', __name__, url_prefix='/reorder')

@reorder_bp.route('/')
def list_reorder():
    """Lists materials that are below their reorder point."""
    db = get_db()
    materials = db.execute("""
        SELECT m.id, m.nombre, m.stock, m.reorder_point, m.target_stock
        FROM materiales m
        WHERE m.stock < m.reorder_point
        ORDER BY m.nombre
    """).fetchall()
    return render_template('reorder/list.html', materials=materials)

@reorder_bp.route('/check', methods=['POST'])
def check_reorder():
    """Checks for materials below reorder point and flashes a message."""
    db = get_db()
    materials_to_reorder = db.execute("""
        SELECT COUNT(id) FROM materiales WHERE stock < reorder_point
    """).fetchone()[0]

    if materials_to_reorder > 0:
        flash(f'{materials_to_reorder} materiales necesitan ser repuestos.', 'info')
    else:
        flash('No hay materiales para reponer.', 'success')

    return redirect(url_for('reorder.list_reorder'))

@reorder_bp.route('/add', methods=['POST'])
def add_reorder_entry():
    """Adds a new reorder entry for a material."""
    material_id = request.form.get('material_id')
    quantity = request.form.get('quantity')

    if not material_id or not quantity:
        flash('Material ID y cantidad son requeridos.', 'error')
        return redirect(url_for('reorder.list_reorder'))

    try:
        quantity = float(quantity)
    except ValueError:
        flash('La cantidad debe ser un número.', 'error')
        return redirect(url_for('reorder.list_reorder'))

    db = get_db()
    db.execute("""
        INSERT INTO reorder_entries (material_id, quantity_to_order)
        VALUES (?, ?)
    """, (material_id, quantity))
    db.commit()

    flash('Pedido de reposición creado exitosamente.', 'success')
    return redirect(url_for('reorder.list_reorder'))
