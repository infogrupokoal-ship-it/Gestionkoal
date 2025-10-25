# backend/cli.py
import click
from flask.cli import with_appcontext

# Importa tu función real de seeding/inicialización
try:
    from .db import close_db, get_db, init_db_func
except ImportError:
    # Fallback inofensivo si aún no existe; así no rompe el import
    def get_db(): return None
    def close_db(e=None): pass
    def init_db_func(): pass


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Inicializa o actualiza la base de datos a la última migración."""
    from flask_migrate import upgrade
    click.echo("Inicializando o actualizando la base de datos a la última versión...")
    try:
        # Llamar a upgrade() programáticamente
        upgrade()
        click.echo(click.style("Base de datos actualizada correctamente.", fg="green"))
    except Exception as e:
        click.echo(click.style(f"Error durante la actualización de la base de datos: {e}", fg="red"))



@click.command("seed")
@with_appcontext
def seed_command():
    """Siembra la base de datos con datos iniciales (no destructivo)."""
    init_db_func()
    click.echo(click.style("Siembra de datos completada.", fg="green"))


def register_cli(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
