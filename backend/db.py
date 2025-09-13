# backend/db.py
import os
import sqlite3
import click
import re
from flask import current_app, g

def get_db():
    if "db" not in g:
        # Ensure the instance folder exists
        os.makedirs(current_app.instance_path, exist_ok=True)
        db_path = os.path.join(current_app.instance_path, current_app.config["DATABASE"])
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db_func():
    db = get_db()
    
    # Read the master schema file
    schema_path = os.path.join(current_app.root_path, '..', 'archivos proyecto', 'schema_grupokoal.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # Translate PostgreSQL to SQLite syntax
    # This logic is recovered from the old app.py
    schema_sql = schema_sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    schema_sql = schema_sql.replace("TEXT UNIQUE NOT NULL", "TEXT UNIQUE NOT NULL COLLATE NOCASE")
    schema_sql = schema_sql.replace("TEXT UNIQUE", "TEXT UNIQUE COLLATE NOCASE")
    schema_sql = schema_sql.replace("TEXT", "TEXT COLLATE NOCASE")
    schema_sql = schema_sql.replace("TIMESTAMP DEFAULT NOW()", "DATETIME DEFAULT CURRENT_TIMESTAMP")
    schema_sql = schema_sql.replace("DOUBLE PRECISION", "REAL")
    schema_sql = schema_sql.replace("NUMERIC", "REAL")
    schema_sql = schema_sql.replace("JSONB", "TEXT")
    schema_sql = schema_sql.replace("BOOLEAN DEFAULT TRUE", "INTEGER DEFAULT 1")
    schema_sql = schema_sql.replace("BOOLEAN DEFAULT FALSE", "INTEGER DEFAULT 0")
    schema_sql = schema_sql.replace("BOOLEAN", "INTEGER")

    # Remove PostgreSQL-specific functions and triggers
    schema_sql = re.sub(r'CREATE OR REPLACE FUNCTION.*?END; \$\$ LANGUAGE plpgsql;', '', schema_sql, flags=re.DOTALL)
    schema_sql = re.sub(r'CREATE TRIGGER.*?;', '', schema_sql, flags=re.DOTALL)

    # Execute the translated schema
    db.executescript(schema_sql)

    # Also add the error_log table from the new design
    db.execute("""
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

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
