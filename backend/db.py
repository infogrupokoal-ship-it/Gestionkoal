# backend/db.py
import os
import sqlite3
import click
import re
import traceback
from flask import current_app, g

def get_db():
    if "db" not in g:
        try:
            # Ensure the instance folder exists
            os.makedirs(current_app.instance_path, exist_ok=True)
            path = os.path.join(current_app.instance_path, current_app.config["DATABASE"])
            g.db = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            # Log the error to console, as dbmod.log_error would call get_db() again
            print(f"ERROR: Could not connect to database in get_db: {e}")
            import traceback
            traceback.print_exc()
            g.db = None # Set g.db to None to avoid repeated attempts
            return None # Return None to indicate failure
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db_func():
    db = get_db()
    
    # Read the SQLite-compatible schema file from backend/schema.sql
    with current_app.open_resource("schema.sql") as f: # This will look in backend/schema.sql
        schema_sql = f.read().decode("utf-8")
    db.executescript(schema_sql)

def init_app(app):
    app.teardown_appcontext(close_db)

def register_commands(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Initializes the database from the master schema file."""
        init_db_func()
        click.echo("Initialized the database with full schema.")

def log_error(level, message, details=None):
    try:
        db = get_db()
        db.execute(
            "INSERT INTO error_log(level, message, details) VALUES (?,?,?)",
            (level, message, details),
        )
        db.commit()
    except Exception as e:
        # Avoid crashing if logging itself fails
        print(f"Failed to log error to DB: {e}")