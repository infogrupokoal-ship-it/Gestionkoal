import csv
import os
import sqlite3
import sys

# Configuración de la base de datos (ajusta según tu entorno)
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'gestion_avisos.sqlite')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def export_to_csv(filename, table_name, columns):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
        rows = cursor.fetchall()

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(columns)  # Escribir encabezados
            for row in rows:
                csv_writer.writerow([row[col] for col in columns])
        print(f"Exportado {len(rows)} registros de {table_name} a {filename}")

    except sqlite3.Error as e:
        print(f"Error de base de datos al exportar {table_name}: {e}", file=sys.stderr)
    except IOError as e:
        print(f"Error de E/S al escribir {filename}: {e}", file=sys.stderr)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Iniciando respaldo del catálogo...")

    # Columnas para materiales (deben coincidir con tu schema.sql)
    material_columns = [
        "id", "nombre", "descripcion", "categoria", "precio_costo_estimado",
        "precio_venta_sugerido", "unidad_medida", "proveedor_sugerido",
        "stock_minimo", "tiempo_entrega_dias", "observaciones"
    ]
    export_to_csv('respaldo_materiales.csv', 'materiales', material_columns)

    # Columnas para servicios (deben coincidir con tu schema.sql)
    service_columns = [
        "id", "nombre", "descripcion", "categoria", "precio_base_estimado",
        "unidad_medida", "tiempo_estimado_horas", "habilidades_requeridas", "observaciones"
    ]
    export_to_csv('respaldo_servicios.csv', 'servicios', service_columns)

    print("Respaldo del catálogo completado.")
