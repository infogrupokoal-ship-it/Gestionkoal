import os, sqlite3, click
from flask import current_app, g

def get_db():
    if "db" not in g:
        os.makedirs(current_app.instance_path, exist_ok=True)
        path = os.path.join(current_app.instance_path, current_app.config["DATABASE"])
        g.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db_func():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))

def init_app(app):
    app.teardown_appcontext(close_db)

def register_commands(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Inicializa la base de datos."""
        init_db_func()
        click.echo("Initialized the database.")

def log_error(level, message, details=None):
    db = get_db()
    db.execute(
        "INSERT INTO error_log(level, message, details) VALUES (?,?,?)",
        (level, message, details),
    )
    db.commit()
