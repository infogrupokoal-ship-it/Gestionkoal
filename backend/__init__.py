# backend/__init__.py
from flask import Flask, jsonify, request, redirect, url_for, render_template
from . import db as dbmod
import os
import sqlite3
from datetime import datetime
import sys # Forzando nuevo despliegue en Render

def create_app():
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates', static_folder=os.path.join(os.path.dirname(__file__), "..", "static"))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "gestion_avisos.sqlite")),
    )
    # Asegurar carpeta instance
    os.makedirs(app.instance_path, exist_ok=True)
    print(f"Usando BD en: {app.config['DATABASE']}", file=sys.stderr) # Log the DB path

    # --- BD y comando CLI ---
    from . import db
    db.init_app(app)
    db.register_commands(app)

    # --- Auto-init del esquema si la BD está vacía ---
    # with app.app_context():
    #     print("CREATE_APP: Verificando si la BD necesita inicializarse...")
    #     try:
    #         conn = dbmod.get_db()
    #         cursor = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' LIMIT 1")
    #         has_any_table = cursor.fetchone()
    #         if not has_any_table:
    #             print("CREATE_APP: La BD está vacía, llamando a init_db_func()...")
    #             from . import db
    #             db.init_db_func()
    #             print("CREATE_APP: init_db_func() llamado con éxito.")
    #         else:
    #             print("CREATE_APP: La BD ya está inicializada.")
    #     except Exception as e:
    #         print(f"CREATE_APP: ERROR durante la inicialización de la BD: {e}")
    #         import traceback
    #         traceback.print_exc()


    # --- Autenticación ---
    from flask_login import (
        LoginManager, UserMixin, login_user,
        login_required, logout_user, current_user, AnonymousUserMixin
    )
    from werkzeug.security import generate_password_hash, check_password_hash

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    class Anonymous(AnonymousUserMixin):
        def has_permission(self, *_args, **_kwargs):
            return False

    login_manager.anonymous_user = Anonymous

    @app.context_processor
    def inject_helpers():
        def can(perm: str) -> bool:
            return current_user.is_authenticated and current_user.has_permission(perm)
        return {"can": can}

    class User(UserMixin):
        def __init__(self, id, username, password_hash, role=None):
            self.id = str(id)
            self.username = username
            self.password_hash = password_hash
            self.role = role

        @staticmethod
        def from_row(row):
            if not row: return None
            return User(row["id"], row["username"], row["password_hash"], row["role"])

        def has_permission(self, permission_name):
            # Implementación simple de permisos: admin tiene todos los permisos
            return self.role == 'admin'

    def get_user_by_id(user_id):
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return User.from_row(row)

    def get_user_by_username(username):
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return User.from_row(row)

    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(user_id)


    # --- Login (acepta JSON o formulario simple) ---
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html")

        # POST
        data = request.get_json(silent=True) or {}
        username = data.get("username") or request.form.get("username", "")
        password = data.get("password") or request.form.get("password", "")
        user = get_user_by_username(username)
        if not user or not check_password_hash(user.password_hash, password):
            return "Credenciales inválidas", 401
        login_user(user)
        return redirect(url_for("dashboard"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/logout")
    @login_required
    def logout():
        logout_user()
        return "Logout OK", 200

    @app.get("/trabajos")
    @login_required
    def list_trabajos():
        conn = dbmod.get_db()
        # Query para obtener los trabajos con nombres de cliente y encargado
        query = """
            SELECT 
                t.*, 
                c.nombre as client_nombre, 
                u.username as encargado_nombre
            FROM trabajos t
            JOIN clients c ON t.client_id = c.id
            LEFT JOIN users u ON t.encargado_id = u.id
            ORDER BY t.fecha_visita DESC
        """
        cursor = conn.execute(query)
        trabajos = cursor.fetchall()
        return render_template("trabajos/list.html", trabajos=trabajos)

    @app.route("/add_trabajo", methods=["GET", "POST"])
    @login_required
    def add_trabajo():
        if not current_user.has_permission('create_new_job'):
            return "No tienes permiso para crear trabajos", 403

        conn = dbmod.get_db()
        if request.method == "POST":
            # Lógica para guardar el nuevo trabajo (se implementará más adelante)
            # Por ahora, solo redirige a la lista de trabajos.
            return redirect(url_for('list_trabajos'))

        # GET: Muestra el formulario
        cursor = conn.execute("SELECT id, nombre FROM clients ORDER BY nombre")
        clients = cursor.fetchall()
        
        cursor = conn.execute("SELECT u.id, u.username FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE r.name = 'autonomo' ORDER BY u.username")
        autonomos = cursor.fetchall()

        return render_template("trabajos/form.html", 
                                title="Añadir Trabajo", 
                                clients=clients, 
                                autonomos=autonomos, 
                                trabajo={}) # Objeto vacío para un trabajo nuevo

    # --- Rutas de Clientes ---
    @app.route("/clients")
    @login_required
    def list_clients():
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM clients ORDER BY nombre")
        clients = cursor.fetchall()
        return render_template("clients/list.html", clients=clients)

    @app.route("/clients/add", methods=["GET", "POST"])
    @login_required
    def add_client():
        if request.method == "POST":
            # Lógica para guardar el nuevo cliente
            return redirect(url_for('list_clients'))
        return render_template("clients/form.html", title="Añadir Cliente", client={})

    # --- Rutas de Servicios ---
    @app.route("/services")
    @login_required
    def list_services():
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM services ORDER BY name")
        services = cursor.fetchall()
        return render_template("services/list.html", services=services)

    @app.route("/services/add", methods=["GET", "POST"])
    @login_required
    def add_service():
        if request.method == "POST":
            return redirect(url_for('list_services'))
        return render_template("services/form.html", title="Añadir Servicio", service={})

    # --- Rutas de Materiales ---
    @app.route("/materials")
    @login_required
    def list_materials():
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM materials ORDER BY name")
        materials = cursor.fetchall()
        return render_template("materials/list.html", materials=materials)

    @app.route("/materials/add", methods=["GET", "POST"])
    @login_required
    def add_material():
        if request.method == "POST":
            return redirect(url_for('list_materials'))
        return render_template("materials/form.html", title="Añadir Material", material={})

    # --- Rutas de Proveedores ---
    @app.route("/proveedores")
    @login_required
    def list_proveedores():
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM proveedores ORDER BY nombre")
        proveedores = cursor.fetchall()
        return render_template("proveedores/list.html", proveedores=proveedores)

    @app.route("/proveedores/add", methods=["GET", "POST"])
    @login_required
    def add_proveedor():
        if request.method == "POST":
            return redirect(url_for('list_proveedores'))
        return render_template("proveedores/form.html", title="Añadir Proveedor", proveedor={})

    # --- Rutas de Autónomos ---
    @app.route("/freelancers")
    @login_required
    def list_freelancers():
        conn = dbmod.get_db()
        cursor = conn.execute("""
            SELECT u.*, GROUP_CONCAT(r.name, ', ') as roles
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.id IN (SELECT user_id FROM user_roles WHERE role_id = (SELECT id FROM roles WHERE name = 'autonomo'))
            GROUP BY u.id
            ORDER BY u.username
        """)
        freelancers = cursor.fetchall()
        return render_template("freelancers/list.html", freelancers=freelancers)

    # --- Placeholder Routes for Proactive Cleanup ---
    @app.route("/reports/financial")
    @login_required
    def financial_reports():
        return render_template("reports/financial.html", title="Informes Financieros")

    @app.route("/trabajos/approval")
    @login_required
    def job_approval_list():
        return render_template("trabajos/approval.html", title="Aprobación de Trabajos")

    @app.route("/users")
    @login_required
    def list_users():
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT u.*, GROUP_CONCAT(r.name, ', ') as roles FROM users u LEFT JOIN user_roles ur ON u.id = ur.user_id LEFT JOIN roles r ON ur.role_id = r.id GROUP BY u.id ORDER BY u.username")
        users = cursor.fetchall()
        return render_template("users/list.html", users=users)

    @app.route("/notifications")
    @login_required
    def list_notifications():
        return render_template("notifications/list.html", title="Notificaciones")

    @app.route("/profile")
    @login_required
    def user_profile():
        return render_template("users/profile.html", user=current_user, roles=[])

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/register")
    def register():
        return render_template("register.html")

    @app.route("/register/client", methods=["GET", "POST"])
    def register_client():
        if request.method == "POST":
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]
            full_name = request.form.get("full_name")
            phone_number = request.form.get("phone_number")
            address = request.form.get("address")
            dni = request.form.get("dni")

            conn = dbmod.get_db()
            error = None

            if not username: error = "Se requiere un nombre de usuario."
            elif not password: error = "Se requiere una contraseña."
            elif password != confirm_password: error = "Las contraseñas no coinciden."
            elif get_user_by_username(username): error = f"El usuario {username} ya está registrado."
            elif conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone(): error = f"El email {email} ya está registrado."

            if error is None:
                password_hash = generate_password_hash(password)
                cursor = conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash),
                )
                user_id = cursor.lastrowid

                # Assign 'client' role
                client_role_id = conn.execute("SELECT id FROM roles WHERE name = 'client'").fetchone()["id"]
                conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, client_role_id))

                # Insert client-specific data
                conn.execute(
                    "INSERT INTO clients (user_id, nombre, telefono, email, direccion, dni) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, full_name, phone_number, email, address, dni)
                )
                conn.commit()
                return redirect(url_for("login"))
            
            # If there's an error, re-render the form with the error message
            # flash(error, 'error') # Need to implement flash messages
            print(f"Error de registro: {error}") # For debugging

        return render_template("register_client.html")

    @app.route("/register/freelancer", methods=["GET", "POST"])
    def register_freelancer():
        if request.method == "POST":
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]
            full_name = request.form.get("full_name")
            phone_number = request.form.get("phone_number")
            address = request.form.get("address")
            dni = request.form.get("dni")

            # Freelancer specific details
            category = request.form.get("category")
            specialty = request.form.get("specialty")
            city_province = request.form.get("city_province")
            web = request.form.get("web")
            notes = request.form.get("notes")
            source_url = request.form.get("source_url")
            hourly_rate_normal = request.form.get("hourly_rate_normal")
            hourly_rate_tier2 = request.form.get("hourly_rate_tier2")
            hourly_rate_tier3 = request.form.get("hourly_rate_tier3")
            difficulty_surcharge_rate = request.form.get("difficulty_surcharge_rate")

            conn = dbmod.get_db()
            error = None

            if not username: error = "Se requiere un nombre de usuario."
            elif not password: error = "Se requiere una contraseña."
            elif password != confirm_password: error = "Las contraseñas no coinciden."
            elif get_user_by_username(username): error = f"El usuario {username} ya está registrado."
            elif conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone(): error = f"El email {email} ya está registrado."

            if error is None:
                password_hash = generate_password_hash(password)
                cursor = conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash),
                )
                user_id = cursor.lastrowid

                # Assign 'autonomo' role
                autonomo_role_id = conn.execute("SELECT id FROM roles WHERE name = 'autonomo'").fetchone()["id"]
                conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, autonomo_role_id))

                # Insert freelancer-specific data
                conn.execute(
                    "INSERT INTO freelancers (user_id, full_name, phone_number, address, dni, category, specialty, city_province, web, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, full_name, phone_number, address, dni, category, specialty, city_province, web, notes, source_url, hourly_rate_normal, hourly_rate_tier2, hourly_rate_tier3, difficulty_surcharge_rate)
                )
                conn.commit()
                return redirect(url_for("login"))
            
            print(f"Error de registro: {error}") # For debugging

        return render_template("register_freelancer.html")

    @app.route("/register/provider", methods=["GET", "POST"])
    def register_provider():
        if request.method == "POST":
            username = request.form["username"]
            email = request.form["email"]
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]
            full_name = request.form.get("full_name")
            phone_number = request.form.get("phone_number")
            address = request.form.get("address")
            dni = request.form.get("dni")

            # Provider specific details
            company_name = request.form.get("company_name")
            contact_person = request.form.get("contact_person")
            provider_phone = request.form.get("provider_phone")
            provider_email = request.form.get("provider_email")
            provider_address = request.form.get("provider_address")
            service_type = request.form.get("service_type")
            web = request.form.get("web")
            notes = request.form.get("notes")

            conn = dbmod.get_db()
            error = None

            if not username: error = "Se requiere un nombre de usuario."
            elif not password: error = "Se requiere una contraseña."
            elif password != confirm_password: error = "Las contraseñas no coinciden."
            elif get_user_by_username(username): error = f"El usuario {username} ya está registrado."
            elif conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone(): error = f"El email {email} ya está registrado."

            if error is None:
                password_hash = generate_password_hash(password)
                cursor = conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash),
                )
                user_id = cursor.lastrowid

                # Assign 'proveedor' role
                proveedor_role_id = conn.execute("SELECT id FROM roles WHERE name = 'proveedor'").fetchone()["id"]
                conn.execute("INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)", (user_id, proveedor_role_id))

                # Insert provider-specific data
                conn.execute(
                    "INSERT INTO proveedores (user_id, full_name, phone_number, address, dni, company_name, contact_person, provider_phone, provider_email, provider_address, service_type, web, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user_id, full_name, phone_number, address, dni, company_name, contact_person, provider_phone, provider_email, provider_address, service_type, web, notes)
                )
                conn.commit()
                return redirect(url_for("login"))
            
            print(f"Error de registro: {error}") # For debugging

        return render_template("register_provider.html")

    # --- Ruta de salud ---
    @app.get("/debug/db")
    def debug_db():
        from . import db as dbmod
        import os, json
        info = {}
        info["instance_path"] = app.instance_path
        info["database_config"] = app.config.get("DATABASE")
        try:
            conn = dbmod.get_db()
            info["db_connected"] = conn is not None
            if conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                rows = cursor.fetchall()
                info["tables"] = [r["name"] for r in rows]
                info["db_exists"] = os.path.exists(app.config["DATABASE"])
        except Exception as e:
            info["error"] = str(e)
        return jsonify(info), 200

    @app.get("/healthz")
    def healthz():
        return "OK", 200

    # --- Ruta raíz (redirige a login) ---
    @app.get("/")
    def index():
        return redirect(url_for("login"))

    # --- Manejador global de errores: guarda en error_log ---
    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback # Added here
        # Get full traceback
        traceback_str = traceback.format_exc()
        
        # Print directly to console for debugging
        print(f"APPLICATION ERROR: {e}", file=sys.stderr)
        print(traceback_str, file=sys.stderr)
        
        # Attempt to log to DB (optional, but keep for now)
        try:
            conn = None
            try:
                instance_path = app.instance_path
                os.makedirs(instance_path, exist_ok=True)
                db_path = os.path.join(instance_path, app.config["DATABASE"])
                conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
                conn.row_factory = sqlite3.Row
                
                conn.execute(
                    "INSERT INTO error_log(level, message, details, created_at) VALUES (?,?,?,?)",
                    ("ERROR", str(e), traceback_str, datetime.now().isoformat()),
                )
                conn.commit()
            except Exception as db_log_e:
                print(f"ERROR: Failed to log error to DB: {db_log_e}", file=sys.stderr)
            finally:
                if conn:
                    conn.close()
        except Exception as outer_e:
            # If even the outer try-except fails, print everything
            print(f"CRITICAL ERROR: Error handler failed: {outer_e}", file=sys.stderr)
            print(f"Original Exception: {e}", file=sys.stderr)
            print(f"Original Traceback: {traceback_str}", file=sys.stderr)

        return ("Se produjo un error. Revisar /logs.", 500)

    import click
    from flask.cli import with_appcontext

    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @with_appcontext
    def create_user(username, password):
        """Crea un usuario con contraseña hasheada."""
        conn = dbmod.get_db()
        if get_user_by_username(username):
            click.echo("Ya existe un usuario con ese username.")
            return
        conn.execute(
            "INSERT INTO users(username, password_hash, role) VALUES (?,?,?)",
            (username, generate_password_hash(password), "admin"),
        )
        conn.commit()
        click.echo(f"Usuario '{username}' creado.")

    return app