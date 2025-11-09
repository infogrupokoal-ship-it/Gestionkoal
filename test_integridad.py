# test_integridad.py
import os
from backend import create_app
from backend.models import get_table_class
from flask import url_for

app = create_app()
with app.app_context():
    print("✅ App creada con éxito")

    # Verificar modelos críticos
    for tabla in ["tickets", "clientes", "presupuestos", "users"]:
        try:
            cls = get_table_class(tabla)
            print(f"✅ Modelo cargado: {tabla}")
        except Exception as e:
            print(f"❌ Error cargando modelo {tabla}: {e}")

    # Verificar rutas importantes
    client = app.test_client()
    rutas = ["/", "/quick_task/add", "/clients", "/quotes", "/reports"]
    for ruta in rutas:
        r = client.get(ruta)
        status = "✅" if r.status_code == 200 else f"❌ ({r.status_code})"
        print(f"{status} Ruta {ruta}")

    # Verificar existencia de imágenes referenciadas (simple check)
    static_files = [
        "static/img/logo_koala.jpg",
    ]
    for path in static_files:
        exists = os.path.exists(path)
        print(f"{'✅' if exists else '❌'} Archivo {path}")
