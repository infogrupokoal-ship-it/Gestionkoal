# backend/pricing_endpoints.py
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, g
from flask_login import login_required, current_user
from sqlalchemy import text

from backend.extensions import db
from backend.pricing import get_market_rate, get_effective_rate, set_override, maybe_adjust_market_suggested
from backend.models import get_table_class

bp = Blueprint("pricing", __name__, url_prefix="/pricing")


@bp.route("/professions")
@login_required
def list_profession_rates():
    if not current_user.has_permission("manage_profession_rates"):
        flash("No tienes permiso para ver las tarifas de profesión.", "error")
        return redirect(url_for("index"))

    ProfessionRate = get_table_class("profession_rates")
    rates = db.session.query(ProfessionRate).order_by(ProfessionRate.nombre).all()
    return render_template("pricing/profession_rates.html", rates=rates)


@bp.route("/professions/add", methods=["GET", "POST"])
@login_required
def add_profession_rate():
    if not current_user.has_permission("manage_profession_rates"):
        flash("No tienes permiso para añadir tarifas de profesión.", "error")
        return redirect(url_for("pricing.list_profession_rates"))

    if request.method == "POST":
        code = request.form["code"].strip().lower()
        nombre = request.form["nombre"].strip()
        precio_min = request.form.get("precio_min", type=float)
        precio_sugerido_hora = request.form.get("precio_sugerido_hora", type=float)
        precio_max = request.form.get("precio_max", type=float)
        error = None

        if not code or not nombre or precio_min is None or precio_sugerido_hora is None or precio_max is None:
            error = "Todos los campos son obligatorios."
        elif not (precio_min <= precio_sugerido_hora <= precio_max):
            error = "El precio sugerido debe estar entre el mínimo y el máximo."
        
        if error is None:
            try:
                ProfessionRate = get_table_class("profession_rates")
                new_rate = ProfessionRate(
                    code=code,
                    nombre=nombre,
                    precio_min=precio_min,
                    precio_sugerido_hora=precio_sugerido_hora,
                    precio_max=precio_max
                )
                db.session.add(new_rate)
                db.session.commit()
                flash("Tarifa de profesión añadida correctamente.", "success")
                return redirect(url_for("pricing.list_profession_rates"))
            except Exception as e:
                db.session.rollback()
                flash(f"Error al añadir la tarifa de profesión: {e}", "error")
        else:
            flash(error, "error")

    return render_template("pricing/profession_rate_form.html", title="Añadir Tarifa de Profesión", rate=None)


@bp.route("/professions/<int:rate_id>/edit", methods=["GET", "POST"])
@login_required
def edit_profession_rate(rate_id):
    if not current_user.has_permission("manage_profession_rates"):
        flash("No tienes permiso para editar tarifas de profesión.", "error")
        return redirect(url_for("pricing.list_profession_rates"))

    ProfessionRate = get_table_class("profession_rates")
    rate = db.session.query(ProfessionRate).get_or_404(rate_id)

    if request.method == "POST":
        code = request.form["code"].strip().lower()
        nombre = request.form["nombre"].strip()
        precio_min = request.form.get("precio_min", type=float)
        precio_sugerido_hora = request.form.get("precio_sugerido_hora", type=float)
        precio_max = request.form.get("precio_max", type=float)
        error = None

        if not code or not nombre or precio_min is None or precio_sugerido_hora is None or precio_max is None:
            error = "Todos los campos son obligatorios."
        elif not (precio_min <= precio_sugerido_hora <= precio_max):
            error = "El precio sugerido debe estar entre el mínimo y el máximo."

        if error is None:
            try:
                rate.code = code
                rate.nombre = nombre
                rate.precio_min = precio_min
                rate.precio_sugerido_hora = precio_sugerido_hora
                rate.precio_max = precio_max
                rate.updated_at = datetime.now()
                db.session.commit()
                flash("Tarifa de profesión actualizada correctamente.", "success")
                return redirect(url_for("pricing.list_profession_rates"))
            except Exception as e:
                db.session.rollback()
                flash(f"Error al actualizar la tarifa de profesión: {e}", "error")
        else:
            flash(error, "error")

    return render_template("pricing/profession_rate_form.html", title="Editar Tarifa de Profesión", rate=rate)


@bp.route("/professions/<int:rate_id>/delete", methods=["POST"])
@login_required
def delete_profession_rate(rate_id):
    if not current_user.has_permission("manage_profession_rates"):
        flash("No tienes permiso para eliminar tarifas de profesión.", "error")
        return redirect(url_for("pricing.list_profession_rates"))

    ProfessionRate = get_table_class("profession_rates")
    rate = db.session.query(ProfessionRate).get_or_404(rate_id)

    try:
        db.session.delete(rate)
        db.session.commit()
        flash("Tarifa de profesión eliminada correctamente.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la tarifa de profesión: {e}", "error")

    return redirect(url_for("pricing.list_profession_rates"))


@bp.route("/effective/<string:profession_code>")
@login_required
def get_effective_rate_endpoint(profession_code):
    user_id = request.args.get("user_id", type=int) or current_user.id
    rate = get_effective_rate(user_id, profession_code)
    return jsonify({"profession_code": profession_code, "effective_rate": rate})


@bp.route("/override", methods=["POST"])
@login_required
def set_override_endpoint():
    user_id = request.form.get("user_id", type=int) or current_user.id
    profession_code = request.form["profession_code"].strip().lower()
    precio_hora = request.form.get("precio_hora", type=float)
    comentario = request.form.get("comentario")
    motivo_dificultad = request.form.get("motivo_dificultad", type=int, default=0)

    if not profession_code or precio_hora is None:
        return jsonify({"error": "Código de profesión y precio por hora son obligatorios."}), 400

    # Ensure the user can only set overrides for themselves or if they have manage_users permission
    if user_id != current_user.id and not current_user.has_permission("manage_users"):
        return jsonify({"error": "No tienes permiso para establecer tarifas para otros usuarios."}), 403

    try:
        set_override(user_id, profession_code, precio_hora, comentario, motivo_dificultad)
        return jsonify({"message": "Override de tarifa guardado correctamente."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al guardar el override de tarifa: {e}"}), 500


@bp.route("/changes")
@login_required
def list_rate_changes():
    if not current_user.has_permission("view_reports"):
        flash("No tienes permiso para ver el historial de cambios de tarifas.", "error")
        return redirect(url_for("index"))

    profession_code = request.args.get("profession_code", "").strip().lower()
    RateChangeLog = get_table_class("rate_change_log")
    User = get_table_class("users")

    query = db.session.query(RateChangeLog, User.username).join(User, RateChangeLog.user_id == User.id)
    if profession_code:
        query = query.filter(RateChangeLog.profession_code == profession_code)
    
    changes = query.order_by(RateChangeLog.created_at.desc()).all()

    return render_template("pricing/rate_change_log.html", changes=changes, profession_code=profession_code)
