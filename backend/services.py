from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import text

from backend.auth import login_required
from backend.extensions import db

bp = Blueprint("services", __name__, url_prefix="/services")


@bp.route("/")
@login_required
def list_services():
    try:
        services = db.session.execute(
            text(
                "SELECT id, name, description, price, category FROM servicios ORDER BY name"
            )
        ).fetchall()
        return render_template("services/list.html", services=services)
    except Exception as e:
        current_app.logger.error(f"Error in list_services: {e}", exc_info=True)
        flash("Ocurrió un error al cargar los servicios.", "error")
        return redirect(url_for("index"))


@bp.route("/<int:service_id>")
@login_required
def view_service(service_id):
    try:
        service = db.session.execute(
            text("SELECT * FROM services WHERE id = :service_id"),
            {"service_id": service_id},
        ).fetchone()

        if service is None:
            flash("Servicio no encontrado.", "error")
            return redirect(url_for("services.list_services"))

        return render_template("services/view.html", service=service)
    except Exception as e:
        current_app.logger.error(f"Error in view_service: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el servicio.", "error")
        return redirect(url_for("services.list_services"))


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_service():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        category = request.form["category"]
        error = None

        if not name:
            error = "Name is required."
        elif not price:
            error = "Price is required."

        if error is None:
            try:
                db.session.execute(
                    text(
                        "INSERT INTO services (name, description, price, category) VALUES (:name, :description, :price, :category)"
                    ),
                    {
                        "name": name,
                        "description": description,
                        "price": price,
                        "category": category,
                    },
                )
                db.session.commit()
                flash("Service added successfully.", "success")
                return redirect(url_for("services.list_services"))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error in add_service: {e}", exc_info=True)
                error = f"An error occurred: {e}"

        flash(error)

    return render_template("services/add.html")


@bp.route("/<int:service_id>/edit", methods=("GET", "POST"))
@login_required
def edit_service(service_id):
    try:
        service = db.session.execute(
            text(
                "SELECT id, name, description, price, category FROM services WHERE id = :service_id"
            ),
            {"service_id": service_id},
        ).fetchone()

        if service is None:
            flash("Service not found.", "error")
            return redirect(url_for("services.list_services"))

        if request.method == "POST":
            name = request.form["name"]
            description = request.form["description"]
            price = request.form["price"]
            category = request.form["category"]
            error = None

            if not name:
                error = "Name is required."
            elif not price:
                error = "Price is required."

            if error is None:
                try:
                    db.session.execute(
                        text(
                            "UPDATE services SET name = :name, description = :description, price = :price, category = :category WHERE id = :service_id"
                        ),
                        {
                            "name": name,
                            "description": description,
                            "price": price,
                            "category": category,
                            "service_id": service_id,
                        },
                    )
                    db.session.commit()
                    flash("Service updated successfully.", "success")
                    return redirect(url_for("services.list_services"))
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(
                        f"Error in edit_service: {e}", exc_info=True
                    )
                    error = f"An error occurred: {e}"

            flash(error)

        return render_template("services/edit.html", service=service)
    except Exception as e:
        current_app.logger.error(f"Error in edit_service: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el servicio para editar.", "error")
        return redirect(url_for("services.list_services"))


@bp.route("/<int:service_id>/delete", methods=("POST",))
@login_required
def delete_service(service_id):
    try:
        db.session.execute(
            text("DELETE FROM services WHERE id = :service_id"),
            {"service_id": service_id},
        )
        db.session.commit()
        flash("Service deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting service: {e}", exc_info=True)
        flash(f"Error deleting service: {e}", "error")

    return redirect(url_for("services.list_services"))
