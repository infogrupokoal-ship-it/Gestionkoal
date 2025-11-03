import logging
from backend import create_app
from backend.llm import ask_gemini_json
from backend.db_utils import insertar_material, insertar_servicio
from backend.extensions import db

def main():
    # Inicializar la aplicación Flask y contexto de aplicación
    app = create_app()
    with app.app_context():
        # Configurar logging para salida por consola
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        # Lista predefinida de descripciones de trabajos
        trabajos = [
            "Instalación de aire acondicionado",
            "Cambio de grifo que gotea",
            "Reparación de interruptor eléctrico",
            "Mantenimiento preventivo de climatización",
            "Renovación de cuarto de baño",
            "Reparación de tubería de agua",
            "Instalación de enchufe eléctrico",
            "Revisión de sistema de calefacción",
            "Colocación de azulejos en cocina",
            "Ajuste de válvula de gas"
        ]

        # Procesar cada descripción de trabajo
        for descripcion in trabajos:
            logger.info(f"Consultando Gemini para '{descripcion}'...")
            # Llamada a Gemini (se espera respuesta JSON con 'materiales' y 'servicios')
            # Usamos el prompt_id 'catalogo_materiales_servicios' que definimos en gemini_seed_prompt.txt
            gemini_resp = ask_gemini_json("catalogo_materiales_servicios", {"descripcion": descripcion})
            if not gemini_resp:
                logger.warning(f"No se obtuvo respuesta para '{descripcion}'")
                continue

            materiales = gemini_resp.get("materiales", [])
            servicios = gemini_resp.get("servicios", [])
            count_mat = 0
            count_srv = 0

            # Insertar cada material en la BD
            for mat in materiales:
                try:
                    insertar_material(mat) # Corregido: pasar el diccionario completo
                    count_mat += 1
                except Exception as e:
                    logger.error(f"Error al insertar material '{mat.get("nombre")}': {e}")

            # Insertar cada servicio en la BD
            for srv in servicios:
                try:
                    insertar_servicio(srv) # Corregido: pasar el diccionario completo
                    count_srv += 1
                except Exception as e:
                    logger.error(f"Error al insertar servicio '{srv.get("nombre")}': {e}")

            # Registrar cuántos ítems se insertaron
            logger.info(f"{count_mat} materiales y {count_srv} servicios insertados para '{descripcion}'")

        # Guardar todos los cambios en la base de datos
        db.session.commit()

if __name__ == "__main__":
    main()
