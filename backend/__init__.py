# backend/__init__.py
from flask import Flask, jsonify, request
from . import db as dbmod

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE="backend.sqlite",
    )

    # --- BD y comando CLI ---
    from . import db
    db.init_app(app)
    db.register_commands(app)

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
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return User.from_row(row)

    def get_user_by_username(username):
        conn = dbmod.get_db()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
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
        return "Login OK", 200

    @app.get("/logout")
    @login_required
    def logout():
        logout_user()
        return "Logout OK", 200

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return f"Hola, {current_user.username}. Dashboard OK.", 200

    # --- Ruta de salud ---
    @app.get("/")
    def index():
        return "OK: gestion_avisos running", 200

    # --- Ejemplo: logs últimos N (opcional) ---
    @app.get("/logs")
    def logs():
        try:
            limit = int(request.args.get("limit", 20))
        except Exception:
            limit = 20
        conn = dbmod.get_db()
        rows = conn.execute(
            "SELECT id, level, message, details, created_at "
            "FROM error_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        # Convert sqlite3.Row objects to dictionaries
        results = []
        for row in rows:
            results.append({col: row[col] for col in row.keys()})
        return jsonify(results), 200

    # --- Ruta IA con Gemini: import tardío dentro de la función ---
    @app.post("/ia")
    def ia():
        from .gemini_client import generate  # <- Import aquí, NO arriba
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "Di 'OK: IA lista'")
        temperature = float(data.get("temperature", 0.2))
        system = data.get("system", "Eres un asistente técnico de Grupo Koal, breve y claro.")
        text = generate(prompt=prompt, system=system, temperature=temperature)
        return text, 200

    # --- Manejador global de errores: guarda en error_log ---
    @app.errorhandler(Exception)
    def handle_exception(e):
        try:
            dbmod.log_error("ERROR", str(e), repr(e))
        except Exception:
            pass
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