# backend/__init__.py
from flask import Flask, jsonify, request, redirect, url_for, render_template, g
from flask_login import current_user # Added for root route
from . import db as dbmod
import os
import sqlite3
from datetime import datetime
import logging

def create_app():
    import sys # Moved import sys here to ensure it's bound
    app = Flask(__name__, instance_relative_config=True,
                template_folder='../templates',
                static_folder=os.path.join(os.path.dirname(__file__), "..", "static"))

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        DATABASE=os.environ.get('DATABASE_PATH', os.path.join(app.instance_path, 'gestion_avisos.sqlite')),
        UPLOAD_FOLDER=os.environ.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'uploads')),
    )

    # load the instance config, if it exists, when not testing
    app.config.from_pyfile('config.py', silent=True)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Configurar logger y registrar ruta de BD
    app.logger.setLevel(logging.INFO)
    app.logger.info("Usando BD en: %s", app.config.get("DATABASE"))

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
        LoginManager, login_user,
        login_required, logout_user, current_user, AnonymousUserMixin
    )
    from backend.auth import User # Import User class

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

    @app.before_request
    def load_logged_in_user_to_g():
        g.user = current_user

    def get_user_by_id(user_id):
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User.from_row(cursor)

    def get_user_by_username(username):
        conn = dbmod.get_db()
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return User.from_row(cursor)

    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(user_id)


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

    # --- Ruta raíz (Dashboard o Login) ---
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return render_template("dashboard.html")
        else:
            return redirect(url_for("auth.login"))

    # --- Health Check ---
    @app.route("/healthz")
    def health_check():
        return jsonify({"status": "ok"}), 200

    @app.route("/debug/users")
    def debug_users():
        conn = dbmod.get_db()
        users = conn.execute("SELECT id, username, role FROM users").fetchall()
        return jsonify([dict(user) for user in users])

    from flask import send_from_directory

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    from . import db
    db.init_app(app)
    db.register_commands(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import jobs
    app.register_blueprint(jobs.bp)

    from . import clients
    app.register_blueprint(clients.bp)

    from . import services
    app.register_blueprint(services.bp)

    from . import materials
    app.register_blueprint(materials.bp)

    from . import providers
    app.register_blueprint(providers.bp)

    from . import freelancers
    app.register_blueprint(freelancers.bp)

    from . import users
    app.register_blueprint(users.bp)

    from . import about
    app.register_blueprint(about.bp)

    from . import reports
    app.register_blueprint(reports.bp)

    from . import notifications
    app.register_blueprint(notifications.bp)

    from . import profile
    app.register_blueprint(profile.bp)

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