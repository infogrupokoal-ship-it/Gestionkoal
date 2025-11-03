import logging
from backend import create_app
from backend.llm import ask_gemini_json
from backend.db_utils import insertar_material, insertar_servicio
from backend.extensions import db

def main():
    app = create_app()
    with app.app_context():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)

        trabajos_extendidos = [
            "Instalación de aire acondicionado split en dormitorio",
            "Reparación de fuga en tubería de lavabo de cocina",
            "Sustitución de interruptor de luz averiado en salón",
            "Mantenimiento preventivo de caldera de gas mural",
            "Renovación completa de cuarto de baño pequeño",
            "Desatasco de desagüe de ducha",
            "Instalación de varios enchufes en oficina",
            "Revisión anual de sistema de calefacción central",
            "Colocación de azulejos en pared de cocina",
            "Ajuste y revisión de válvula de gas principal",
            "Reparación de persiana enrollable atascada",
            "Montaje de muebles de cocina modulares",
            "Pintura de habitación individual",
            "Instalación de ventilador de techo con luz",
            "Reparación de cisterna de inodoro que pierde agua",
            "Cambio de bombillas halógenas a LED en toda la casa",
            "Limpieza profunda de conductos de aire acondicionado",
            "Instalación de termo eléctrico de 80 litros",
            "Reparación de puerta de armario descolgada",
            "Sellado de ventanas para evitar filtraciones de aire",
            "Revisión de instalación de gas y certificado",
            "Instalación de mampara de ducha",
            "Reparación de gotera en tejado",
            "Montaje de estanterías de pladur",
            "Pulido y abrillantado de suelo de mármol",
            "Instalación de cerradura de seguridad en puerta principal",
            "Mantenimiento de jardín pequeño (poda, riego)",
            "Reparación de electrodoméstico (lavadora no centrifuga)",
            "Instalación de sistema de alarma básico",
            "Revisión de fontanería general en vivienda"
        ]

        total_materiales_insertados = 0
        total_servicios_insertados = 0

        for i, descripcion in enumerate(trabajos_extendidos):
            logger.info(f"[{i+1}/{len(trabajos_extendidos)}] Consultando Gemini para '{descripcion}'...")
            
            gemini_resp = ask_gemini_json("catalogo_materiales_servicios", {"descripcion": descripcion})
            if not gemini_resp:
                logger.warning(f"No se obtuvo respuesta para '{descripcion}'. Saltando.")
                continue

            materiales = gemini_resp.get("materiales", [])
            servicios = gemini_resp.get("servicios", [])
            count_mat = 0
            count_srv = 0

            for mat in materiales:
                try:
                    insertar_material(mat)
                    count_mat += 1
                except Exception as e:
                    logger.error(f"Error al insertar material '{mat.get("nombre")}' para '{descripcion}': {e}")

            for srv in servicios:
                try:
                    insertar_servicio(srv)
                    count_srv += 1
                except Exception as e:
                    logger.error(f"Error al insertar servicio '{srv.get("nombre")}' para '{descripcion}': {e}")

            total_materiales_insertados += count_mat
            total_servicios_insertados += count_srv
            logger.info(f"{count_mat} materiales y {count_srv} servicios insertados para '{descripcion}'. Totales: {total_materiales_insertados} materiales, {total_servicios_insertados} servicios.")

        db.session.commit()
        logger.info(f"Proceso de poblamiento masivo completado. Total de materiales insertados: {total_materiales_insertados}. Total de servicios insertados: {total_servicios_insertados}.")

if __name__ == "__main__":
    main()
