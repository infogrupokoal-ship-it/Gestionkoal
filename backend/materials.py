from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend.auth import login_required
from backend.models import get_table_class
from backend.extensions import db
from backend.forms import MaterialForm
from backend.market_study import get_market_study_for_material  # New import
from datetime import datetime

bp = Blueprint("materials", __name__, url_prefix="/materials")

@bp.route("/")
@login_required
def list_materials():
    if not current_user.has_permission("manage_materials"):
        flash("No tienes permiso para gestionar materiales.", "error")
        return redirect(url_for("index"))

    Material = get_table_class("materiales")
    materials = db.session.query(Material).all()
    return render_template("materials/list.html", materials=materials)


@bp.route("/<int:material_id>")
@login_required
def view_material(material_id):
    if not current_user.has_permission("manage_materials"):
        flash("No tienes permiso para ver este material.", "error")
        return redirect(url_for("index"))

    Material = get_table_class("materiales")
    Provider = get_table_class("providers")

    material = (
        db.session.query(Material, Provider.nombre.label("proveedor_nombre"))
        .outerjoin(Provider, Material.proveedor_id == Provider.id)
        .filter(Material.id == material_id)
        .first()
    )

    if material is None:
        flash("Material no encontrado.", "error")
        return redirect(url_for("materials.list_materials"))

    return render_template("materials/view.html", material=material)


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_material():
    if not current_user.has_permission("manage_materials"):
        flash("No tienes permiso para añadir materiales.", "error")
        return redirect(url_for("materials.list_materials"))

    form = MaterialForm()
    Provider = get_table_class("providers")
    form.proveedor_id.choices = [(p.id, p.nombre) for p in db.session.query(Provider).all()]
    form.proveedor_id.choices.insert(0, (0, '-- Seleccionar Proveedor --'))

    if form.validate_on_submit():
        sku = form.sku.data.strip()
        if not sku:
            Material = get_table_class("materiales")
            last_sku_row = (
                db.session.query(Material.sku)
                .filter(Material.sku.like("MAT-%"))
                .order_by(Material.sku.desc())
                .first()
            )
            if last_sku_row and last_sku_row.sku:
                try:
                    last_num = int(last_sku_row.sku.split("-")[1])
                    new_num = last_num + 1
                    sku = f"MAT-{new_num:04d}"
                except (IndexError, ValueError):
                    sku = "MAT-0001"
            else:
                sku = "MAT-0001"

        try:
            Material = get_table_class("materiales")
            new_material = Material(
                sku=sku,
                nombre=form.nombre.data,
                categoria=form.categoria.data,
                unidad_medida=form.unidad_medida.data, # Corregido de 'unidad' a 'unidad_medida'
                stock_minimo=form.stock_minimo.data, # Corregido de 'stock_min' a 'stock_minimo'
                ubicacion=form.ubicacion.data,
                precio_costo_estimado=form.precio_costo_estimado.data, # Corregido de 'costo_unitario'
                precio_venta_sugerido=form.precio_venta_sugerido.data, # Nuevo campo
                proveedor_sugerido=form.proveedor_sugerido.data, # Nuevo campo
                tiempo_entrega_dias=form.tiempo_entrega_dias.data, # Nuevo campo
                observaciones=form.observaciones.data, # Nuevo campo
                stock_actual=form.stock_actual.data, # Nuevo campo
                fecha_ultimo_ingreso=form.fecha_ultimo_ingreso.data, # Nuevo campo
                cantidad_total_usada=form.cantidad_total_usada.data, # Nuevo campo
                proveedor_id=form.proveedor_id.data if form.proveedor_id.data != 0 else None,
            )
            db.session.add(new_material)
            db.session.commit()
            flash(f"¡Material añadido correctamente! SKU asignado: {sku}")
            return redirect(url_for("materials.list_materials"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ocurrió un error inesperado: {e}", "error")

    return render_template("materials/form.html", form=form, title="Añadir Material")


@bp.route("/<int:material_id>/edit", methods=("GET", "POST"))
@login_required
def edit_material(material_id):
    if not current_user.has_permission("manage_materials"):
        flash("No tienes permiso para editar materiales.", "error")
        return redirect(url_for("materials.list_materials"))

    Material = get_table_class("materiales")
    material = db.session.query(Material).filter_by(id=material_id).first()

    if material is None:
        flash("Material no encontrado.", "error")
        return redirect(url_for("materials.list_materials"))

    form = MaterialForm(obj=material)
    Provider = get_table_class("providers")
    form.proveedor_id.choices = [(p.id, p.nombre) for p in db.session.query(Provider).all()]
    form.proveedor_id.choices.insert(0, (0, '-- Seleccionar Proveedor --'))

    if form.validate_on_submit():
        try:
            material.sku = form.sku.data
            material.nombre = form.nombre.data
            material.categoria = form.categoria.data
            material.unidad_medida = form.unidad_medida.data
            material.stock_minimo = form.stock_minimo.data
            material.ubicacion = form.ubicacion.data
            material.precio_costo_estimado = form.precio_costo_estimado.data
            material.precio_venta_sugerido = form.precio_venta_sugerido.data
            material.proveedor_sugerido = form.proveedor_sugerido.data
            material.tiempo_entrega_dias = form.tiempo_entrega_dias.data
            material.observaciones = form.observaciones.data
            material.stock_actual = form.stock_actual.data
            material.fecha_ultimo_ingreso = form.fecha_ultimo_ingreso.data
            material.cantidad_total_usada = form.cantidad_total_usada.data
            material.proveedor_id = form.proveedor_id.data if form.proveedor_id.data != 0 else None
            db.session.commit()
            flash("¡Material actualizado correctamente!")
            return redirect(url_for("materials.list_materials"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ocurrió un error inesperado: {e}", "error")

    proveedor_nombre = ''
    if material.proveedor_id:
        Provider = get_table_class("providers")
        proveedor = db.session.query(Provider).filter_by(id=material.proveedor_id).first()
        if proveedor:
            proveedor_nombre = proveedor.nombre

    market_study_data = get_market_study_for_material(material_id)
    return render_template(
        "materials/form.html",
        form=form,
        title="Editar Material",
        market_study_data=market_study_data,
        proveedor_nombre=proveedor_nombre
    )


@bp.route("/reorder-needed")
@login_required
def reorder_needed_list():
    if not current_user.has_permission("manage_materials"):
        flash("No tienes permiso para ver esta página.", "error")
        return redirect(url_for("index"))

    Material = get_table_class("materiales")
    materials_to_reorder = db.session.query(Material).filter(Material.stock_actual <= Material.stock_minimo).all()
    return render_template("materials/reorder_list.html", materials=materials_to_reorder)