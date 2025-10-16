# backend/cli.py
import os
import click
from flask.cli import with_appcontext
from flask import current_app

# Importa tu función real de seeding/inicialización
try:
    from .db import get_db, close_db, init_db_func
except ImportError:
    # Fallback inofensivo si aún no existe; así no rompe el import
    def get_db(): return None
    def close_db(e=None): pass
    def init_db_func(): pass


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Crea las tablas de la base de datos desde schema.sql."""
    db = get_db()
    if db is None:
        click.echo(click.style("Error: No se pudo obtener la conexión a la base de datos.", fg="red"))
        return

    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
    
    if not os.path.exists(schema_path):
        click.echo(click.style(f"Error: No se encuentra el fichero schema.sql en la ruta: {schema_path}", fg="red"))
        return

    click.echo("Creando base de datos desde schema.sql...")
    with open(schema_path, 'rb') as f:
        _sql = f.read().decode("utf-8")
        db.executescript(_sql)
    
    click.echo(click.style("Base de datos inicializada con el esquema maestro.", fg="green"))


@click.command("seed")
@with_appcontext
def seed_command():
    """Siembra la base de datos con datos iniciales (no destructivo)."""
    init_db_func()
    click.echo(click.style("Siembra de datos completada.", fg="green"))


def register_cli(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
