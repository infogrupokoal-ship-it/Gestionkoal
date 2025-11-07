# backend/cli.py
import os

import click
from flask.cli import with_appcontext

from backend.data_quality import (
    check_duplicate_materials,
    check_low_stock_materials,
    check_services_without_price,
    get_average_material_usage_per_ticket,
    get_material_category_stats,
    get_service_category_stats,
)
from backend.db_utils import init_db_func
from backend.extensions import db


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Inicializa o actualiza la base de datos a la ultima migracion."""
    from flask_migrate import upgrade

    click.echo("Inicializando la base de datos desde schema.sql...")
    with db.engine.connect() as connection:
        with open(os.path.join(os.path.dirname(__file__), 'schema.sql')) as f:
            sql_script = f.read()
            for statement in sql_script.split(';'):
                if statement.strip():
                    connection.exec_driver_sql(statement)
    db.session.commit()
    click.echo("Base de datos inicializada. Aplicando migraciones...")
    try:
        # Llamar a upgrade() programaticamente
        upgrade()
        click.echo(click.style("Base de datos actualizada correctamente.", fg="green"))
    except Exception as e:
        click.echo(
            click.style(
                f"Error durante la actualizacion de la base de datos: {e}", fg="red"
            )
        )
    init_db_func()


@click.command("seed")
@with_appcontext
def seed_command():
    """Siembra la base de datos con datos iniciales (no destructivo)."""
    init_db_func()
    click.echo(click.style("Siembra de datos completada.", fg="green"))


@click.command("check-data-quality")
@with_appcontext
def check_data_quality_command():
    """Realiza un chequeo de calidad de datos y muestra un resumen."""
    click.echo(click.style("\n--- Chequeo de Calidad de Datos ---", fg="cyan"))

    # Materiales Duplicados
    duplicates = check_duplicate_materials()
    if duplicates:
        click.echo(click.style("\nMateriales Duplicados (Nombre, Proveedor):", fg="yellow"))
        for name, provider_id, count in duplicates:
            click.echo(f"  - Nombre: {name}, Proveedor ID: {provider_id}, Cantidad: {count}")
    else:
        click.echo(click.style("\nNo se encontraron materiales duplicados.", fg="green"))

    # Servicios sin Precio Definido
    services_without_price = check_services_without_price()
    if services_without_price:
        click.echo(click.style("\nServicios sin Precio Definido:", fg="yellow"))
        for service in services_without_price:
            click.echo(f"  - ID: {service.id}, Nombre: {service.nombre}")
    else:
        click.echo(click.style("\nTodos los servicios tienen precio definido.", fg="green"))

    # Materiales con Stock Bajo
    low_stock_materials = check_low_stock_materials()
    if low_stock_materials:
        click.echo(click.style("\nMateriales con Stock Bajo (<= Stock Mínimo):", fg="yellow"))
        for material in low_stock_materials:
            click.echo(f"  - ID: {material.id}, Nombre: {material.nombre}, Stock Actual: {material.stock_actual}, Stock Mínimo: {material.stock_minimo}")
    else:
        click.echo(click.style("\nNo hay materiales con stock bajo.", fg="green"))

    # Estadísticas de Materiales por Categoría
    material_stats = get_material_category_stats()
    click.echo(click.style("\nEstadísticas de Materiales por Categoría:", fg="blue"))
    if material_stats:
        for categoria, count, total_stock in material_stats:
            click.echo(f"  - Categoría: {categoria or 'N/A'}, Cantidad: {count}, Stock Total: {total_stock}")
    else:
        click.echo("  No hay materiales registrados.")

    # Estadísticas de Servicios por Categoría
    service_stats = get_service_category_stats()
    click.echo(click.style("\nEstadísticas de Servicios por Categoría:", fg="blue"))
    if service_stats:
        for categoria, count, avg_price in service_stats:
            click.echo(f"  - Categoría: {categoria or 'N/A'}, Cantidad: {count}, Precio Promedio: {avg_price:.2f}€")
    else:
        click.echo("  No hay servicios registrados.")

    # Uso Promedio de Materiales por Ticket
    avg_material_usage = get_average_material_usage_per_ticket()
    click.echo(click.style("\nUso Promedio de Materiales por Ticket:", fg="blue"))
    click.echo(f"  - {avg_material_usage:.2f} unidades de material por ticket en promedio.")

    click.echo(click.style("\n--- Chequeo de Calidad de Datos Completado ---", fg="cyan"))

def register_cli(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
    app.cli.add_command(check_data_quality_command)
