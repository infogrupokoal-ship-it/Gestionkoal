from flask import Flask, request, jsonify
from . import db as dbmod

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE="backend.sqlite",
    )

    # Inicializar DB y comando CLI
    from . import db
    db.init_app(app)
    db.register_commands(app)

    # --- Rutas básicas ---
    @app.get("/")
    def index():
        return "OK: gestion_avisos running", 200

    @app.get("/boom")
    def boom():
        raise RuntimeError("Error de prueba para error_log")

    @app.get("/logs")
    def logs():
        try:
            limit = int(request.args.get("limit", 20))
        except Exception:
            limit = 20
        conn = dbmod.get_db()
        rows = conn.execute(
            "SELECT id, level, message, details, created_at FROM error_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return jsonify([dict(r) for r in rows]), 200

    # Manejador global de errores -> guarda en error_log
    @app.errorhandler(Exception)
    def handle_exception(e):
        try:
            dbmod.log_error("ERROR", str(e), repr(e))
        except Exception:
            pass
        return ("Se produjo un error. Revisar /logs.", 500)

    return app
