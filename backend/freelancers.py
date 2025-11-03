from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import text

from backend.auth import login_required
from backend.extensions import db

bp = Blueprint("freelancers", __name__, url_prefix="/freelancers")


@bp.route("/dashboard")
@login_required
def dashboard():
    try:
        assigned_jobs = db.session.execute(
            text(
                """
            SELECT
                t.id, t.titulo, t.descripcion, t.estado, t.fecha_creacion, t.fecha_inicio,
                c.nombre AS client_name
            FROM tickets t
            JOIN clientes c ON t.cliente_id = c.id
            WHERE t.asignado_a = :user_id
            ORDER BY t.fecha_creacion DESC
            """
            ),
            {"user_id": g.user.id},
        ).fetchall()

        return render_template(
            "freelancers/dashboard.html", assigned_jobs=assigned_jobs
        )
    except Exception as e:
        current_app.logger.error(f"Error en el dashboard de autónomos: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el dashboard.", "error")
        return redirect(url_for("index"))


@bp.route("/")
@login_required
def list_freelancers():
    try:
        freelancers_data = db.session.execute(
            text(
                """
            SELECT f.id, u.username, f.category, f.specialty, f.hourly_rate_normal
            FROM freelancers f
            JOIN users u ON f.user_id = u.id
            ORDER BY u.username
            """
            )
        ).fetchall()
        return render_template("freelancers/list.html", freelancers=freelancers_data)
    except Exception as e:
        current_app.logger.error(f"Error al listar los autónomos: {e}", exc_info=True)
        flash("Ocurrió un error al cargar los autónomos.", "error")
        return redirect(url_for("index"))


@bp.route("/<int:freelancer_id>")
@login_required
def view_freelancer(freelancer_id):
    try:
        freelancer = db.session.execute(
            text(
                """
            SELECT
                u.id, u.username, u.email, u.telefono,
                f.category, f.specialty, f.city_province, f.web, f.notes, f.source_url,
                f.hourly_rate_normal, f.hourly_rate_tier2, f.hourly_rate_tier3, f.difficulty_surcharge_rate, f.recargo_zona, f.recargo_dificultad
            FROM users u
            JOIN freelancers f ON u.id = f.user_id
            WHERE u.id = :freelancer_id AND u.role = "autonomo"
            """
            ),
            {"freelancer_id": freelancer_id},
        ).fetchone()

        if freelancer is None:
            flash("Autónomo no encontrado.", "error")
            return redirect(url_for("freelancers.list_freelancers"))

        return render_template("freelancers/view.html", freelancer=freelancer)
    except Exception as e:
        current_app.logger.error(f"Error al ver el autónomo: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el autónomo.", "error")
        return redirect(url_for("freelancers.list_freelancers"))


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add_freelancer():
    try:
        if request.method == "POST":
            user_id = request.form["user_id"]
            category = request.form["category"]
            specialty = request.form["specialty"]
            city_province = request.form["city_province"]
            web = request.form["web"]
            notes = request.form["notes"]
            source_url = request.form["source_url"]
            hourly_rate_normal = request.form["hourly_rate_normal"]
            hourly_rate_tier2 = request.form["hourly_rate_tier2"]
            hourly_rate_tier3 = request.form["hourly_rate_tier3"]
            difficulty_surcharge_rate = request.form["difficulty_surcharge_rate"]
            recargo_zona = request.form["recargo_zona"]
            recargo_dificultad = request.form["recargo_dificultad"]
            error = None

            if not user_id:
                error = "El usuario es obligatorio."

            if error is None:
                try:
                    db.session.execute(
                        text(
                            "INSERT INTO freelancers (user_id, category, specialty, city_province, web, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate, recargo_zona, recargo_dificultad) VALUES (:user_id, :category, :specialty, :city_province, :web, :notes, :source_url, :hourly_rate_normal, :hourly_rate_tier2, :hourly_rate_tier3, :difficulty_surcharge_rate, :recargo_zona, :recargo_dificultad)"
                        ),
                        {
                            "user_id": user_id,
                            "category": category,
                            "specialty": specialty,
                            "city_province": city_province,
                            "web": web,
                            "notes": notes,
                            "source_url": source_url,
                            "hourly_rate_normal": hourly_rate_normal,
                            "hourly_rate_tier2": hourly_rate_tier2,
                            "hourly_rate_tier3": hourly_rate_tier3,
                            "difficulty_surcharge_rate": difficulty_surcharge_rate,
                            "recargo_zona": recargo_zona,
                            "recargo_dificultad": recargo_dificultad,
                        },
                    )
                    db.session.commit()
                    flash("Autónomo añadido correctamente.", "success")
                    return redirect(url_for("freelancers.list_freelancers"))
                except Exception as e:
                    db.session.rollback()
                    error = f"Ocurrió un error: {e}"

            flash(error)

        users = db.session.execute(
            text(
                "SELECT id, username FROM users WHERE id NOT IN (SELECT user_id FROM freelancers)"
            )
        ).fetchall()
        return render_template("freelancers/add.html", users=users)
    except Exception as e:
        current_app.logger.error(f"Error al añadir el autónomo: {e}", exc_info=True)
        flash("Ocurrió un error al añadir el autónomo.", "error")
        return redirect(url_for("freelancers.list_freelancers"))


@bp.route("/<int:freelancer_id>/edit", methods=("GET", "POST"))
@login_required
def edit_freelancer(freelancer_id):
    try:
        freelancer = db.session.execute(
            text(
                """
            SELECT f.id, f.user_id, u.username, f.category, f.specialty, f.hourly_rate_normal
            FROM freelancers f
            JOIN users u ON f.user_id = u.id
            WHERE f.id = :freelancer_id
            """
            ),
            {"freelancer_id": freelancer_id},
        ).fetchone()

        if freelancer is None:
            flash("Autónomo no encontrado.", "error")
            return redirect(url_for("freelancers.list_freelancers"))

        if request.method == "POST":
            user_id = request.form["user_id"]
            category = request.form["category"]
            specialty = request.form["specialty"]
            hourly_rate_normal = request.form["hourly_rate_normal"]
            error = None

            if not user_id or not category or not specialty or not hourly_rate_normal:
                error = "Usuario, Categoría, Especialidad y Tarifa por Hora son obligatorios."

            if error is None:
                try:
                    db.session.execute(
                        text(
                            "UPDATE freelancers SET user_id = :user_id, category = :category, specialty = :specialty, hourly_rate_normal = :hourly_rate_normal WHERE id = :freelancer_id"
                        ),
                        {
                            "user_id": user_id,
                            "category": category,
                            "specialty": specialty,
                            "hourly_rate_normal": hourly_rate_normal,
                            "freelancer_id": freelancer_id,
                        },
                    )
                    db.session.commit()
                    flash("Autónomo actualizado correctamente.", "success")
                    return redirect(url_for("freelancers.list_freelancers"))
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(
                        f"Error in edit_freelancer: {e}", exc_info=True
                    )
                    error = f"An error occurred: {e}"

            flash(error)

        users = db.session.execute(text("SELECT id, username FROM users")).fetchall()
        return render_template(
            "freelancers/edit.html", freelancer=freelancer, users=users
        )
    except Exception as e:
        current_app.logger.error(f"Error al editar el autónomo: {e}", exc_info=True)
        flash("Ocurrió un error al cargar el autónomo para editar.", "error")
        return redirect(url_for("freelancers.list_freelancers"))


@bp.route("/<int:freelancer_id>/delete", methods=("POST",))
@login_required
def delete_freelancer(freelancer_id):
    try:
        db.session.execute(
            text("DELETE FROM freelancers WHERE id = :freelancer_id"),
            {"freelancer_id": freelancer_id},
        )
        db.session.commit()
        flash("Autónomo eliminado correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar el autónomo: {e}", exc_info=True)
        flash(f"Error al eliminar el autónomo: {e}", "error")

    return redirect(url_for("freelancers.list_freelancers"))
