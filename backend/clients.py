from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from backend.extensions import db
from backend.forms import ClientForm
from backend.models import get_table_class

bp = Blueprint("clients", __name__, url_prefix="/clients")


@bp.route("/")
@login_required
def list_clients():
    current_app.logger.debug(
        "list_clients access user=%s role=%s",
        getattr(current_user, "username", None),
        getattr(current_user, "role", None),
    )
    Client = get_table_class("clientes")
    if not current_user.has_permission("manage_clients"):
        flash("No tienes permiso para gestionar clientes.", "error")
        return redirect(url_for("auth.login"))

    clients = db.session.query(Client).all()
    return render_template("clients/list.html", clients=clients)


@bp.route("/<int:client_id>")
@login_required
def view_client(client_id):
    Client = get_table_class("clientes")
    if not current_user.has_permission("manage_clients"):
        flash("No tienes permiso para ver este cliente.", "error")
        return redirect(url_for("index"))

    client = db.session.query(Client).get_or_404(client_id)
    return render_template("clients/view.html", client=client)


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_client():
    Client = get_table_class("clientes")
    if not current_user.has_permission("manage_clients"):
        flash("No tienes permiso para añadir clientes.", "error")
        return redirect(url_for("clients.list_clients"))

    form = ClientForm()
    if form.validate_on_submit():
        try:
            new_client = Client(
                nombre=form.nombre.data,
                telefono=form.telefono.data,
                email=form.email.data,
                nif=form.nif.data,
                is_ngo=form.is_ngo.data,
            )
            db.session.add(new_client)
            db.session.commit()
            flash("Cliente añadido correctamente.", "success")
            return redirect(url_for("clients.list_clients"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ocurrió un error al añadir el cliente: {e}", "error")

    return render_template("clients/form.html", form=form, title="Añadir Cliente")


@bp.route("/<int:client_id>/edit", methods=("GET", "POST"))
@login_required
def edit_client(client_id):
    Client = get_table_class("clientes")
    if not current_user.has_permission("manage_clients"):
        flash("No tienes permiso para editar clientes.", "error")
        return redirect(url_for("clients.list_clients"))

    client = db.session.query(Client).get_or_404(client_id)
    form = ClientForm(obj=client)

    if form.validate_on_submit():
        try:
            client.nombre = form.nombre.data
            client.telefono = form.telefono.data
            client.email = form.email.data
            client.nif = form.nif.data
            client.is_ngo = form.is_ngo.data
            db.session.commit()
            flash("Cliente actualizado correctamente.", "success")
            return redirect(url_for("clients.view_client", client_id=client_id))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "error")

    return render_template(
        "clients/form.html", form=form, client=client, title="Editar Cliente"
    )


@bp.route("/<int:client_id>/delete", methods=("POST",))
@login_required
def delete_client(client_id):
    Client = get_table_class("clientes")
    if not current_user.has_permission("manage_clients"):
        flash("No tienes permiso para eliminar clientes.", "error")
        return redirect(url_for("clients.list_clients"))

    client = db.session.query(Client).get_or_404(client_id)

    try:
        # A correct way to check for dependencies
        Ticket = get_table_class("tickets")
        linked_jobs = db.session.query(Ticket).filter_by(cliente_id=client_id).first()

        if linked_jobs:
            flash(
                "No se puede eliminar el cliente porque tiene trabajos asociados.",
                "error",
            )
            return redirect(url_for("clients.list_clients"))

        db.session.delete(client)
        db.session.commit()
        flash("Cliente eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el cliente: {e}", "error")

    return redirect(url_for("clients.list_clients"))
