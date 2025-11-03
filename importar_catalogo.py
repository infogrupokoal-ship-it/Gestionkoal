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

def import_materials_from_csv(filename):
    print(f"Iniciando importación de materiales desde {filename}...")
    imported_count = 0
    skipped_count = 0
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                try:
                    # Convertir tipos de datos
                    row['precio_costo_estimado'] = float(row.get('precio_costo_estimado', 0.0))
                    row['precio_venta_sugerido'] = float(row.get('precio_venta_sugerido', 0.0))
                    row['stock_minimo'] = int(row.get('stock_minimo', 0))
                    row['tiempo_entrega_dias'] = int(row.get('tiempo_entrega_dias', 0))

                    # Intentar insertar o actualizar
                    cursor.execute("""
                        INSERT INTO materiales
                        (nombre, descripcion, categoria, precio_costo_estimado, precio_venta_sugerido,
                         unidad_medida, proveedor_sugerido, stock_minimo, tiempo_entrega_dias, observaciones)
                        VALUES (:nombre, :descripcion, :categoria, :precio_costo_estimado, :precio_venta_sugerido,
                                :unidad_medida, :proveedor_sugerido, :stock_minimo, :tiempo_entrega_dias, :observaciones)
                        ON CONFLICT(nombre) DO UPDATE SET
                            descripcion=excluded.descripcion,
                            categoria=excluded.categoria,
                            precio_costo_estimado=excluded.precio_costo_estimado,
                            precio_venta_sugerido=excluded.precio_venta_sugerido,
                            unidad_medida=excluded.unidad_medida,
                            proveedor_sugerido=excluded.proveedor_sugerido,
                            stock_minimo=excluded.stock_minimo,
                            tiempo_entrega_dias=excluded.tiempo_entrega_dias,
                            observaciones=excluded.observaciones
                    """, row)
                    imported_count += 1
                except Exception as e:
                    print(f"[ERROR] Saltando material '{row.get('nombre', 'N/A')}' debido a un error: {e}", file=sys.stderr)
                    skipped_count += 1
        conn.commit()
        print(f"Importación de materiales completada. Importados: {imported_count}, Saltados: {skipped_count}")

    except FileNotFoundError:
        print(f"[ERROR] Archivo no encontrado: {filename}", file=sys.stderr)
    except sqlite3.Error as e:
        print(f"[ERROR] Error de base de datos al importar materiales: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Ocurrió un error inesperado al importar materiales: {e}", file=sys.stderr)
    finally:
        if conn:
            conn.close()

def import_services_from_csv(filename):
    print(f"Iniciando importación de servicios desde {filename}...")
    imported_count = 0
    skipped_count = 0
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                try:
                    # Convertir tipos de datos
                    row['precio_base_estimado'] = float(row.get('precio_base_estimado', 0.0))
                    row['tiempo_estimado_horas'] = float(row.get('tiempo_estimado_horas', 0.0))

                    # Intentar insertar o actualizar
                    cursor.execute("""
                        INSERT INTO servicios
                        (nombre, descripcion, categoria, precio_base_estimado, unidad_medida,
                         tiempo_estimado_horas, habilidades_requeridas, observaciones)
                        VALUES (:nombre, :descripcion, :categoria, :precio_base_estimado, :unidad_medida,
                                :tiempo_estimado_horas, :habilidades_requeridas, :observaciones)
                        ON CONFLICT(nombre) DO UPDATE SET
                            descripcion=excluded.descripcion,
                            categoria=excluded.categoria,
                            precio_base_estimado=excluded.precio_base_estimado,
                            unidad_medida=excluded.unidad_medida,
                            tiempo_estimado_horas=excluded.tiempo_estimado_horas,
                            habilidades_requeridas=excluded.habilidades_requeridas,
                            observaciones=excluded.observaciones
                    """, row)
                    imported_count += 1
                except Exception as e:
                    print(f"[ERROR] Saltando servicio '{row.get('nombre', 'N/A')}' debido a un error: {e}", file=sys.stderr)
                    skipped_count += 1
        conn.commit()
        print(f"Importación de servicios completada. Importados: {imported_count}, Saltados: {skipped_count}")

    except FileNotFoundError:
        print(f"[ERROR] Archivo no encontrado: {filename}", file=sys.stderr)
    except sqlite3.Error as e:
        print(f"[ERROR] Error de base de datos al importar servicios: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Ocurrió un error inesperado al importar servicios: {e}", file=sys.stderr)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python importar_catalogo.py <archivo_materiales.csv> [archivo_servicios.csv]", file=sys.stderr)
        sys.exit(1)

    materials_file = sys.argv[1]
    import_materials_from_csv(materials_file)

    if len(sys.argv) > 2:
        services_file = sys.argv[2]
        import_services_from_csv(services_file)
