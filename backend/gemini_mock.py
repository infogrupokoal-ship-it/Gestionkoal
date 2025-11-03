# backend/gemini_mock.py

def get_mock_response(task_key, vars):
    if task_key == "catalogo_materiales_servicios":
        descripcion = vars.get("descripcion", "").lower()
        if "aire acondicionado" in descripcion:
            return {
                "materiales": [
                    {
                        "nombre": "Gas refrigerante R410A",
                        "descripcion": "Cilindro de gas refrigerante para sistemas de aire acondicionado.",
                        "categoria": "Climatización",
                        "precio_costo_estimado": 80.00,
                        "precio_venta_sugerido": 120.00,
                        "unidad_medida": "kg",
                        "proveedor_sugerido": "ClimaRepuestos",
                        "stock_minimo": 2,
                        "tiempo_entrega_dias": 1,
                        "observaciones": "Requiere manipulación por personal certificado."
                    },
                    {
                        "nombre": "Tubería de cobre aislada 1/4 pulgada",
                        "descripcion": "Tubería de cobre pre-aislada para conexiones de unidades de AC.",
                        "categoria": "Climatización",
                        "precio_costo_estimado": 4.50,
                        "precio_venta_sugerido": 6.75,
                        "unidad_medida": "metro",
                        "proveedor_sugerido": "ClimaRepuestos",
                        "stock_minimo": 20,
                        "tiempo_entrega_dias": 1,
                        "observaciones": "Para línea de líquido."
                    }
                ],
                "servicios": [
                    {
                        "nombre": "Instalación básica de AC Split",
                        "descripcion": "Instalación de unidad de aire acondicionado tipo split, hasta 3 metros de tubería.",
                        "categoria": "Climatización",
                        "precio_base_estimado": 180.00,
                        "unidad_medida": "servicio",
                        "tiempo_estimado_horas": 3.0,
                        "habilidades_requeridas": "Técnico de climatización certificado",
                        "observaciones": "No incluye obra civil mayor."
                    },
                    {
                        "nombre": "Carga de gas refrigerante",
                        "descripcion": "Recarga de gas refrigerante en sistemas de aire acondicionado con fuga detectada y reparada.",
                        "categoria": "Climatización",
                        "precio_base_estimado": 90.00,
                        "unidad_medida": "servicio",
                        "tiempo_estimado_horas": 1.5,
                        "habilidades_requeridas": "Técnico de climatización certificado",
                        "observaciones": "Precio base, el coste del gas es aparte."
                    }
                ]
            }
        elif "grifo que gotea" in descripcion:
            return {
                "materiales": [
                    {
                        "nombre": "Junta de goma para grifo",
                        "descripcion": "Junta tórica de goma para sellado de grifos.",
                        "categoria": "Fontanería",
                        "precio_costo_estimado": 0.50,
                        "precio_venta_sugerido": 1.50,
                        "unidad_medida": "unidad",
                        "proveedor_sugerido": "Ferretería Local",
                        "stock_minimo": 50,
                        "tiempo_entrega_dias": 0,
                        "observaciones": "Varias medidas disponibles."
                    },
                    {
                        "nombre": "Grifo monomando lavabo",
                        "descripcion": "Grifo monomando cromado para lavabo de baño.",
                        "categoria": "Fontanería",
                        "precio_costo_estimado": 35.00,
                        "precio_venta_sugerido": 60.00,
                        "unidad_medida": "unidad",
                        "proveedor_sugerido": "Bricomart",
                        "stock_minimo": 5,
                        "tiempo_entrega_dias": 3,
                        "observaciones": "Modelo estándar."
                    }
                ],
                "servicios": [
                    {
                        "nombre": "Cambio de grifo",
                        "descripcion": "Sustitución de grifo antiguo por uno nuevo, incluyendo desconexión y conexión.",
                        "categoria": "Fontanería",
                        "precio_base_estimado": 50.00,
                        "unidad_medida": "servicio",
                        "tiempo_estimado_horas": 1.0,
                        "habilidades_requeridas": "Fontanero",
                        "observaciones": "No incluye coste del grifo."
                    },
                    {
                        "nombre": "Reparación de fuga en grifo",
                        "descripcion": "Diagnóstico y reparación de fugas menores en grifos, cambio de juntas o cartuchos.",
                        "categoria": "Fontanería",
                        "precio_base_estimado": 40.00,
                        "unidad_medida": "servicio",
                        "tiempo_estimado_horas": 0.75,
                        "habilidades_requeridas": "Fontanero",
                        "observaciones": "Materiales pequeños incluidos."
                    }
                ]
            }
        elif "interruptor eléctrico" in descripcion:
            return {
                "materiales": [
                    {
                        "nombre": "Interruptor simple",
                        "descripcion": "Interruptor de pared simple para encendido/apagado de luz.",
                        "categoria": "Electricidad",
                        "precio_costo_estimado": 2.00,
                        "precio_venta_sugerido": 4.00,
                        "unidad_medida": "unidad",
                        "proveedor_sugerido": "Electricidad Express",
                        "stock_minimo": 20,
                        "tiempo_entrega_dias": 1,
                        "observaciones": "Color blanco, modelo estándar."
                    },
                    {
                        "nombre": "Caja de mecanismo universal",
                        "descripcion": "Caja empotrable para mecanismos eléctricos.",
                        "categoria": "Electricidad",
                        "precio_costo_estimado": 1.00,
                        "precio_venta_sugerido": 2.00,
                        "unidad_medida": "unidad",
                        "proveedor_sugerido": "Electricidad Express",
                        "stock_minimo": 30,
                        "tiempo_entrega_dias": 1,
                        "observaciones": "Profundidad estándar."
                    }
                ],
                "servicios": [
                    {
                        "nombre": "Reparación/Cambio de interruptor",
                        "descripcion": "Diagnóstico y sustitución de interruptor eléctrico defectuoso.",
                        "categoria": "Electricidad",
                        "precio_base_estimado": 35.00,
                        "unidad_medida": "servicio",
                        "tiempo_estimado_horas": 0.5,
                        "habilidades_requeridas": "Electricista",
                        "observaciones": "No incluye interruptor de diseño especial."
                    },
                    {
                        "nombre": "Revisión de circuito eléctrico",
                        "descripcion": "Verificación de continuidad y fallos en un circuito eléctrico simple.",
                        "categoria": "Electricidad",
                        "precio_base_estimado": 50.00,
                        "unidad_medida": "servicio",
                        "tiempo_estimado_horas": 1.0,
                        "habilidades_requeridas": "Electricista autorizado",
                        "observaciones": "No incluye reparaciones mayores."
                    }
                ]
            }
        # Añadir más casos elif para otras descripciones de trabajo si es necesario
        else:
            # Respuesta genérica si la descripción no coincide con mocks específicos
            return {
                "materiales": [
                    {
                        "nombre": "Kit de herramientas básicas",
                        "descripcion": "Juego de destornilladores, alicates y martillo.",
                        "categoria": "Ferretería",
                        "precio_costo_estimado": 15.00,
                        "precio_venta_sugerido": 25.00,
                        "unidad_medida": "unidad",
                        "proveedor_sugerido": "Amazon",
                        "stock_minimo": 5,
                        "tiempo_entrega_dias": 2,
                        "observaciones": "Útil para cualquier trabajo."
                    }
                ],
                "servicios": [
                    {
                        "nombre": "Diagnóstico general",
                        "descripcion": "Evaluación inicial de un problema no especificado.",
                        "categoria": "Mantenimiento General",
                        "precio_base_estimado": 30.00,
                        "unidad_medida": "servicio",
                        "tiempo_estimado_horas": 0.5,
                        "habilidades_requeridas": "Técnico general",
                        "observaciones": "El coste se descuenta de la reparación final."
                    }
                ]
            }
    return {}
