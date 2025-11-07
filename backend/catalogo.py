from flask import Blueprint, render_template, request

from backend.db_utils import (
    get_distinct_material_categories,
    get_distinct_material_providers,
    get_distinct_service_categories,
    get_distinct_service_skills,
    obtener_materiales,
    obtener_servicios,
)

catalogo_bp = Blueprint("catalogo", __name__)

@catalogo_bp.route("/materiales")
def listar_materiales():
    q = request.args.get("q", "").lower()
    categoria_filtro = request.args.get("categoria", "")
    proveedor_filtro = request.args.get("proveedor", "")

    materiales = obtener_materiales()

    if q:
        materiales = [m for m in materiales if q in m["nombre"].lower() or q in m.get("descripcion", "").lower()]
    if categoria_filtro:
        materiales = [m for m in materiales if m.get("categoria") == categoria_filtro]
    if proveedor_filtro:
        materiales = [m for m in materiales if m.get("proveedor_sugerido") == proveedor_filtro]

    categorias = get_distinct_material_categories()
    proveedores = get_distinct_material_providers()

    return render_template("materiales.html", materiales=materiales, q=q, categorias=categorias, proveedores=proveedores, selected_categoria=categoria_filtro, selected_proveedor=proveedor_filtro)

@catalogo_bp.route("/servicios")
def listar_servicios():
    q = request.args.get("q", "").lower()
    categoria_filtro = request.args.get("categoria", "")
    habilidad_filtro = request.args.get("habilidad", "")

    servicios = obtener_servicios()

    if q:
        servicios = [s for s in servicios if q in s["nombre"].lower() or q in s.get("descripcion", "").lower()]
    if categoria_filtro:
        servicios = [s for s in servicios if s.get("categoria") == categoria_filtro]
    if habilidad_filtro:
        servicios = [s for s in servicios if s.get("habilidades_requeridas") == habilidad_filtro]

    categorias = get_distinct_service_categories()
    habilidades = get_distinct_service_skills()

    return render_template("servicios.html", servicios=servicios, q=q, categorias=categorias, habilidades=habilidades, selected_categoria=categoria_filtro, selected_habilidad=habilidad_filtro)

@catalogo_bp.route("/exportar_csv")
def exportar_csv():
    import csv
    from io import StringIO

    from flask import make_response

    # Exportar Materiales
    materiales = obtener_materiales()
    si_materiales = StringIO()
    cw_materiales = csv.writer(si_materiales)

    # Escribir encabezados de materiales
    if materiales:
        cw_materiales.writerow(materiales[0].keys())
    # Escribir datos de materiales
    for mat in materiales:
        cw_materiales.writerow(mat.values())

    # Exportar Servicios
    servicios = obtener_servicios()
    si_servicios = StringIO()
    cw_servicios = csv.writer(si_servicios)

    # Escribir encabezados de servicios
    if servicios:
        cw_servicios.writerow(servicios[0].keys())
    # Escribir datos de servicios
    for srv in servicios:
        cw_servicios.writerow(srv.values())

    # Combinar ambos CSV en un solo archivo para descarga
    output = StringIO()
    output.write("Materiales\n")
    output.write(si_materiales.getvalue())
    output.write("\n\nServicios\n")
    output.write(si_servicios.getvalue())

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=catalogo_gestionkoal.csv"
    response.headers["Content-type"] = "text/csv"
    return response
