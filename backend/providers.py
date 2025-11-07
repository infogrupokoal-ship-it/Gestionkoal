from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user

from backend.auth import login_required
from backend.extensions import db
from backend.forms import ProviderForm  # Importar el formulario
from backend.models import get_table_class

bp = Blueprint("providers", __name__, url_prefix="/proveedores")


@bp.route("/")
@login_required
def list_providers():
    if not current_user.has_permission("manage_providers"):
        flash("No tienes permiso para gestionar proveedores.", "error")
        return redirect(url_for("index"))

    Provider = get_table_class("providers")
    providers = db.session.query(Provider).all()
    return render_template("proveedores/list.html", providers=providers)


@bp.route("/<int:provider_id>")
@login_required
def view_provider(provider_id):
    if not current_user.has_permission("manage_providers"):
        flash("No tienes permiso para ver este proveedor.", "error")
        return redirect(url_for("index"))
    Provider = get_table_class("providers")
    proveedor = db.session.query(Provider).filter_by(id=provider_id).first()

    if proveedor is None:
        flash("Proveedor no encontrado.", "error")
        return redirect(url_for("providers.list_providers"))

    return render_template("proveedores/view.html", proveedor=proveedor)


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_provider():
    if not current_user.has_permission("manage_providers"):
        flash("No tienes permiso para añadir proveedores.", "error")
        return redirect(url_for("providers.list_providers"))

    form = ProviderForm()
    if form.validate_on_submit():
        try:
            Provider = get_table_class("providers")
            new_provider = Provider(
                nombre=form.nombre.data,
                contacto=form.contacto.data,
                telefono=form.telefono.data,
                email=form.email.data,
                direccion=form.direccion.data,
                nif=form.nif.data,
                tipo=form.tipo.data,
                is_active=form.is_active.data,
                whatsapp_number=form.whatsapp_number.data,
                whatsapp_opt_in=form.whatsapp_opt_in.data,
            )
            db.session.add(new_provider)
            db.session.commit()
            flash("Proveedor añadido con éxito.", "success")
            return redirect(url_for("providers.list_providers"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al añadir proveedor: {e}", "error")

    return render_template("proveedores/form.html", form=form, title="Añadir Proveedor")


@bp.route("/<int:provider_id>/edit", methods=("GET", "POST"))
@login_required
def edit_provider(provider_id):
    if not current_user.has_permission("manage_providers"):
        flash("No tienes permiso para editar proveedores.", "error")
        return redirect(url_for("providers.list_providers"))

    Provider = get_table_class("providers")
    provider = db.session.query(Provider).filter_by(id=provider_id).first()

    if provider is None:
        flash("Proveedor no encontrado.", "error")
        return redirect(url_for("providers.list_providers"))

    form = ProviderForm(obj=provider)

    if form.validate_on_submit():
        try:
            provider.nombre = form.nombre.data
            provider.contacto = form.contacto.data
            provider.telefono = form.telefono.data
            provider.email = form.email.data
            provider.direccion = form.direccion.data
            provider.nif = form.nif.data
            provider.tipo = form.tipo.data
            provider.is_active = form.is_active.data
            provider.whatsapp_number = form.whatsapp_number.data
            provider.whatsapp_opt_in = form.whatsapp_opt_in.data
            db.session.commit()
            flash("Proveedor actualizado con éxito.", "success")
            return redirect(url_for("providers.list_providers"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar proveedor: {e}", "error")

    return render_template(
        "proveedores/form.html", form=form, provider=provider, title="Editar Proveedor"
    )


@bp.route("/<int:provider_id>/delete", methods=("POST",))
@login_required
def delete_provider(provider_id):
    if not current_user.has_permission("manage_providers"):
        flash("No tienes permiso para eliminar proveedores.", "error")
        return redirect(url_for("providers.list_providers"))

    Provider = get_table_class("providers")
    provider = db.session.query(Provider).filter_by(id=provider_id).first()

    if provider:
        try:
            Material = get_table_class("materiales")
            # Corregir la referencia a proveedor_id
            linked_materials = db.session.query(Material).filter_by(proveedor_id=provider_id).first()

            if linked_materials:
                flash(
                    f"No se puede eliminar el proveedor porque está asignado como principal a {linked_materials.nombre}.",
                    "error",
                )
                return redirect(url_for("providers.list_providers"))

            db.session.delete(provider)
            db.session.commit()
            flash("Proveedor eliminado con éxito.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al eliminar proveedor: {e}", "error")
    else:
        flash("Proveedor no encontrado.", "error")

    return redirect(url_for("providers.list_providers"))
