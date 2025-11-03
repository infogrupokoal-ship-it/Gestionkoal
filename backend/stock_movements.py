from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import login_required
from backend.extensions import db
from backend.models import get_table_class

bp = Blueprint("stock_movements", __name__, url_prefix="/stock_movements")


@bp.route("/")
@login_required
def list_stock_movements():
    StockMovement = get_table_class("stock_movements")
    Material = get_table_class("materiales")
    User = get_table_class("users")

    movements = (
        db.session.query(
            StockMovement.id,
            Material.nombre.label("material_nombre"),
            StockMovement.cantidad,
            StockMovement.tipo,
            StockMovement.fecha,
            User.username.label("responsable"),
        )
        .join(Material, StockMovement.material_id == Material.id)
        .outerjoin(User, StockMovement.responsable == User.id)
        .order_by(StockMovement.fecha.desc())
        .all()
    )
    return render_template("stock_movements/list.html", movements=movements)


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_movement():
    Material = get_table_class("materiales")
    materials = db.session.query(Material).order_by(Material.nombre).all()

    if request.method == "POST":
        material_id = request.form.get("material_id", type=int)
        tipo = request.form.get("tipo")
        cantidad = request.form.get("cantidad", type=float)
        observaciones = request.form.get("observaciones")
        responsable = g.user.id
        error = None

        if not material_id or not tipo or not cantidad:
            error = "Material, Tipo y Cantidad son obligatorios."
        elif cantidad <= 0:
            error = "La cantidad debe ser un número positivo."

        if error is None:
            try:
                StockMovement = get_table_class("stock_movements")
                new_movement = StockMovement(
                    material_id=material_id,
                    tipo=tipo,
                    cantidad=cantidad,
                    responsable=responsable,
                    observaciones=observaciones,
                )
                db.session.add(new_movement)

                material = db.session.query(Material).filter_by(id=material_id).first()
                if tipo == "entrada":
                    material.stock += cantidad
                elif tipo == "salida":
                    material.stock -= cantidad
                
                db.session.commit()

                # --- Reorder Notification Logic ---
                if tipo == 'salida' or tipo == 'ajuste':
                    if material.stock <= material.stock_min:
                        from backend.notifications import add_notification
                        User = get_table_class("users")
                        admins = db.session.query(User).filter(User.role == 'admin').all()
                        message = f"¡Stock bajo! El material '{material.nombre}' (SKU: {material.sku}) tiene solo {material.stock} unidades restantes."
                        for admin in admins:
                            add_notification(db.session, admin.id, message)
                # --- End Reorder Notification Logic ---

                flash("Movimiento de stock añadido correctamente.", "success")
                return redirect(url_for("stock_movements.list_stock_movements"))
            except Exception as e:
                error = f"Ocurrió un error: {e}"
                db.session.rollback()

        flash(error)

    return render_template("stock_movements/form.html", materials=materials, movement=None)