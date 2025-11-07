import os
import sqlite3
from datetime import datetime

# Configuración de la base de datos
DATABASE = os.path.join('instance', 'gestion_avisos.sqlite')

def import_ticket_from_json(json_data):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Insertar o obtener cliente
        cliente_id = None
        if json_data["cliente"]["nombre"] != "Desconocido":
            cursor.execute("SELECT id FROM clientes WHERE nombre = ?", (json_data["cliente"]["nombre"],))
            cliente = cursor.fetchone()
            if cliente:
                cliente_id = cliente[0]
            else:
                cursor.execute(
                    "INSERT INTO clientes (nombre, nif, email) VALUES (?, ?, ?)",
                    (json_data["cliente"]["nombre"], json_data["cliente"]["nif"], json_data["cliente"]["email"])
                )
                cliente_id = cursor.lastrowid
        else:
            # Si el cliente es desconocido, podemos asignarlo a un cliente genérico o dejarlo null
            # Por simplicidad, lo dejaremos null si no hay nombre de cliente
            pass

        # Insertar ticket
        cursor.execute(
            """
            INSERT INTO tickets (
                cliente_id, tipo, prioridad, titulo, descripcion, ubicacion,
                fecha_creacion, estado, creado_por, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_id,
                json_data["tipo"],
                json_data["prioridad"],
                json_data["titulo"],
                json_data["descripcion"],
                json_data["ubicacion"],
                datetime.now().isoformat(),
                "nuevo", # Estado inicial
                1, # Asignar a un usuario por defecto (ej. admin)
                json_data["observaciones"]
            )
        )
        ticket_id = cursor.lastrowid

        # Insertar materiales (si los hay)
        for _material in json_data["materiales"]:
            # Aquí deberías tener una lógica para buscar el material por nombre/SKU
            # y luego insertarlo en job_materials si aplica.
            # Por ahora, solo lo registramos como observación o en un log si no hay tabla específica.
            pass # Lógica para materiales más compleja, requiere tabla de materiales y job_materials

        # Insertar servicios (si los hay)
        for _servicio_name in json_data["servicios"]:
            # Similar a materiales, buscar servicio y luego insertar en job_services
            pass # Lógica para servicios más compleja, requiere tabla de servicios y job_services

        conn.commit()
        print(f"Ticket '{json_data['titulo']}' importado con éxito. ID: {ticket_id}")

    except Exception as e:
        conn.rollback()
        print(f"Error al importar ticket '{json_data['titulo']}': {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    mock_tickets = [
        # JSON 1
        {
          "tipo": "avería de fontanería",
          "prioridad": "media",
          "titulo": "Fuga de agua bajo fregadero de cocina",
          "descripcion": "El cliente reporta una fuga de agua debajo del fregadero de la cocina. El agua gotea y ha formado un charco en el suelo.",
          "ubicacion": "cocina, bajo fregadero",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": [],
          "servicios": ["reparación de fontanería"],
          "observaciones": "Posible necesidad de revisar tuberías o sellado del fregadero."
        },
        # JSON 2
        {
          "tipo": "avería eléctrica",
          "prioridad": "alta",
          "titulo": "Fallo eléctrico en salón, enchufes sin corriente",
          "descripcion": "El cliente informa de un apagón en el salón, los enchufes no funcionan. Ha verificado el cuadro eléctrico y no hay diferenciales bajados, lo que sugiere un problema más allá del diferencial.",
          "ubicacion": "salón",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": [],
          "servicios": ["reparación eléctrica", "diagnóstico de avería"],
          "observaciones": "El problema no parece ser un diferencial. Podría ser un circuito, cableado o un problema en la instalación general."
        },
        # JSON 3
        {
          "tipo": "pedido de material",
          "prioridad": "baja",
          "titulo": "Pedido de bombillas LED GU10 7W luz cálida",
          "descripcion": "El cliente desea pedir 10 unidades de bombillas LED GU10 de 7W con luz cálida. Pregunta por la disponibilidad en stock.",
          "ubicacion": "Desconocido",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": [
            {"nombre": "bombilla LED GU10", "cantidad": 10, "especificaciones": "7W, luz cálida"}
          ],
          "servicios": [],
          "observaciones": "Verificar stock y precio de las bombillas solicitadas. Contactar al cliente para confirmar pedido."
        },
        # JSON 4
        {
          "tipo": "solicitud de presupuesto",
          "prioridad": "media",
          "titulo": "Presupuesto para cambio de ventanas con aislamiento térmico en local",
          "descripcion": "El cliente solicita un presupuesto para la sustitución de todas las ventanas de su local por modelos con aislamiento térmico.",
          "ubicacion": "local",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": [],
          "servicios": ["instalación de ventanas", "aislamiento térmico"],
          "observaciones": "Necesario realizar visita para medir y evaluar el tipo de ventanas y aislamiento requerido."
        },
        # JSON 5
        {
          "tipo": "avería",
          "prioridad": "alta",
          "titulo": "Goteras en el techo del despacho",
          "descripcion": "El cliente reporta la aparición de goteras en el techo del despacho a causa de las lluvias. Las manchas de humedad están aumentando de tamaño.",
          "ubicacion": "despacho, techo",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": [],
          "servicios": ["reparación de tejado/cubierta", "impermeabilización"],
          "observaciones": "Urgente debido a las lluvias y el crecimiento de las manchas. Posible daño estructural o en mobiliario."
        },
        # JSON 6
        {
          "tipo": "avería",
          "prioridad": "media",
          "titulo": "Fallo en cerradura de puerta principal",
          "descripcion": "El cliente informa que la cerradura de la puerta principal está fallando. Presenta dificultad para abrir y ocasionalmente se traba.",
          "ubicacion": "puerta principal",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": ["cerradura", "bombín"],
          "servicios": ["reparación de cerraduras", "sustitución de cerraduras"],
          "observaciones": "Evaluar si es posible reparar o si requiere cambio de cerradura/bombín."
        },
        # JSON 7
        {
          "tipo": "avería",
          "prioridad": "alta",
          "titulo": "Calentador de agua sin funcionar y con pitido",
          "descripcion": "El cliente reporta que no tiene agua caliente desde ayer. El calentador emite un pitido y no enciende. Necesita revisión técnica.",
          "ubicacion": "Desconocido",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": [],
          "servicios": ["reparación de calentador", "diagnóstico de avería"],
          "observaciones": "Urgente por falta de agua caliente. Posible fallo en el encendido, válvula de gas o componente interno."
        },
        # JSON 8
        {
          "tipo": "avería de fontanería",
          "prioridad": "alta",
          "titulo": "Tubería reventada en garaje",
          "descripcion": "El cliente informa de una tubería reventada en el garaje, con salida de agua a mucha presión. Requiere intervención inmediata.",
          "ubicacion": "garaje",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": ["tubería", "abrazaderas", "cinta selladora"],
          "servicios": ["reparación de tuberías", "fontanería de emergencia"],
          "observaciones": "¡URGENTE! Cortar suministro de agua si es posible. Alto riesgo de inundación y daños mayores."
        },
        # JSON 9
        {
          "tipo": "solicitud de servicio",
          "prioridad": "baja",
          "titulo": "Instalación de punto de recarga para coche eléctrico",
          "descripcion": "El cliente está interesado en la instalación de un punto de recarga para coche eléctrico en su aparcamiento y pregunta si ofrecemos este servicio.",
          "ubicacion": "aparcamiento",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": ["punto de recarga", "cableado eléctrico"],
          "servicios": ["instalación eléctrica", "instalación de punto de recarga"],
          "observaciones": "Contactar al cliente para ofrecer información sobre el servicio y posibles presupuestos."
        },
        # JSON 10
        {
          "tipo": "consulta técnica",
          "prioridad": "baja",
          "titulo": "Consulta sobre cambio de iluminación a sensores de movimiento",
          "descripcion": "El cliente consulta si es posible cambiar el sistema de iluminación actual del pasillo por uno con sensores de movimiento.",
          "ubicacion": "pasillo",
          "cliente": {
            "nombre": "Desconocido",
            "nif": None,
            "email": None
          },
          "materiales": ["sensor de movimiento", "luminarias compatibles"],
          "servicios": ["instalación eléctrica", "asesoramiento técnico"],
          "observaciones": "Proporcionar información sobre viabilidad, costes y beneficios de la instalación de sensores de movimiento."
        }
    ]

    for ticket_data in mock_tickets:
        import_ticket_from_json(ticket_data)
