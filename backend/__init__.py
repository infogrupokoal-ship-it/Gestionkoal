# backend/__init__.py
from flask import Flask, jsonify, request, redirect, url_for
from . import db as dbmod
import os
import sqlite3
from datetime import datetime

def create_app():
    app = Flask(__name__, instance_relative_config=True, template_folder='../templates', static_folder=os.path.join(os.path.dirname(__file__), "..", "static"))
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "gestion_avisos.sqlite")),
    )
    # Asegurar carpeta instance
    os.makedirs(app.instance_path, exist_ok=True)
    import sys # Added here
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
        login_required, logout_user, current_user
    )
    from werkzeug.security import generate_password_hash, check_password_hash

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

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
            # HTML mínimo para pruebas rápidas sin plantillas
            return (
                "<form method='post'>Usuario: <input name='username'/> "
                "Password: <input name='password' type='password'/> "
                "<button>Entrar</button></form>", 200
            )

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
        return "Dashboard OK"

    # --- Ruta de salud ---
    @app.get("/healthz")
    def healthz():
        return "ok", 200

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