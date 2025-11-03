from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from backend.db_utils import get_db_connection, get_user_by_id, get_all_users, get_all_roles, update_user_roles, get_user_roles_by_id, get_role_by_id, get_role_by_code, get_total_jobs_by_category, get_most_used_services, get_low_stock_materials, get_estimated_service_hours, get_top_clients
from werkzeug.security import generate_password_hash
import functools

admin_bp = Blueprint("admin", __name__)

# Decorador para verificar si el usuario actual es administrador
def admin_required(f):
    @functools.wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("No tienes permisos para acceder a esta página.", "error")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/admin/users")
@admin_required
def manage_users():
    users = get_all_users()
    roles = get_all_roles()
    users_with_roles = []
    for user in users:
        user_roles = get_user_roles_by_id(user["id"])
        user_role_names = [get_role_by_id(role_id)["code"] for role_id in user_roles]
        users_with_roles.append({"user": user, "roles": user_role_names})
    return render_template("admin/users.html", users=users_with_roles, all_roles=roles)

@admin_bp.route("/admin/user/edit/<int:user_id>", methods=["GET", "POST"])
@admin_required
def edit_user(user_id):
    user = get_user_by_id(user_id)
    if not user:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for("admin.manage_users"))

    all_roles = get_all_roles()
    user_roles = get_user_roles_by_id(user_id)

    if request.method == "POST":
        selected_role_ids = request.form.getlist("roles")
        update_user_roles(user_id, selected_role_ids)
        flash("Roles de usuario actualizados correctamente.", "success")
        return redirect(url_for("admin.manage_users"))

    return render_template("admin/user_form.html", user=user, all_roles=all_roles, user_roles=user_roles)

    return redirect(url_for("admin.manage_users"))

@admin_bp.route("/admin/dashboard_analytics")
@admin_required
def dashboard_analytics():
    total_jobs_by_category = get_total_jobs_by_category()
    most_used_services = get_most_used_services()
    low_stock_materials = get_low_stock_materials()
    estimated_service_hours = get_estimated_service_hours()
    top_clients = get_top_clients()

    return render_template("admin/dashboard_analytics.html",
                           total_jobs_by_category=total_jobs_by_category,
                           most_used_services=most_used_services,
                           low_stock_materials=low_stock_materials,
                           estimated_service_hours=estimated_service_hours,
                           top_clients=top_clients)
