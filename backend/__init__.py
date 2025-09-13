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
        return jsonify([dict(r) for r in rows]), 200

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

    return app