import json
import sqlite3

# Conecta a la base de datos (ajusta la ruta si necesario)
conn = sqlite3.connect('instance/gestion_avisos.sqlite')
cursor = conn.cursor()

# Crea tabla si no existe
cursor.execute('''
CREATE TABLE IF NOT EXISTS mensajes_clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    prioridad TEXT,
    titulo TEXT,
    descripcion TEXT,
    ubicacion TEXT,
    cliente_nombre TEXT,
    cliente_nif TEXT,
    cliente_email TEXT,
    materiales TEXT,
    servicios TEXT,
    observaciones TEXT
)
''')

# Lista de mensajes de prueba en formato JSON (como strings embebidos)
mensajes = [
    {
        "tipo": "avería de fontanería",
        "prioridad": "media",
        "titulo": "Fuga de agua bajo fregadero de cocina",
        "descripcion": "El cliente reporta una fuga de agua debajo del fregadero de la cocina. El agua gotea y ha formado un charco en el suelo.",
        "ubicacion": "cocina, bajo fregadero",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": [],
        "servicios": ["reparación de fontanería"],
        "observaciones": "Posible necesidad de revisar tuberías o sellado del fregadero."
    },
    {
        "tipo": "avería eléctrica",
        "prioridad": "alta",
        "titulo": "Fallo eléctrico en salón, enchufes sin corriente",
        "descripcion": "El cliente informa de un apagón en el salón, los enchufes no funcionan. Ha verificado el cuadro eléctrico y no hay diferenciales bajados.",
        "ubicacion": "salón",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": [],
        "servicios": ["reparación eléctrica", "diagnóstico de avería"],
        "observaciones": "El problema no parece ser un diferencial. Podría ser un circuito, cableado o instalación."
    },
    {
        "tipo": "pedido de material",
        "prioridad": "baja",
        "titulo": "Pedido de bombillas LED GU10 7W luz cálida",
        "descripcion": "El cliente desea pedir 10 unidades de bombillas LED GU10 de 7W con luz cálida.",
        "ubicacion": "Desconocido",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": [
            {"nombre": "bombilla LED GU10", "cantidad": 10, "especificaciones": "7W, luz cálida"}
        ],
        "servicios": [],
        "observaciones": "Verificar stock y precio de las bombillas solicitadas. Contactar al cliente para confirmar pedido."
    },
    {
        "tipo": "solicitud de presupuesto",
        "prioridad": "media",
        "titulo": "Presupuesto para cambio de ventanas con aislamiento térmico en local",
        "descripcion": "El cliente solicita un presupuesto para sustituir todas las ventanas del local por modelos con aislamiento térmico.",
        "ubicacion": "local",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": [],
        "servicios": ["instalación de ventanas", "aislamiento térmico"],
        "observaciones": "Necesario realizar visita para medir y evaluar opciones de ventanas."
    },
    {
        "tipo": "avería",
        "prioridad": "alta",
        "titulo": "Goteras en el techo del despacho",
        "descripcion": "El cliente reporta goteras en el techo del despacho debido a las lluvias. Las manchas de humedad están aumentando.",
        "ubicacion": "despacho, techo",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": [],
        "servicios": ["reparación de tejado", "impermeabilización"],
        "observaciones": "Urgente por riesgo de filtraciones. Podría requerir revisión estructural."
    },
    {
        "tipo": "avería",
        "prioridad": "media",
        "titulo": "Fallo en cerradura de puerta principal",
        "descripcion": "El cliente informa que la cerradura de la puerta principal falla, cuesta abrir y a veces se traba.",
        "ubicacion": "puerta principal",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": ["cerradura", "bombín"],
        "servicios": ["reparación de cerraduras", "sustitución de cerraduras"],
        "observaciones": "Evaluar si requiere reparación o reemplazo completo."
    },
    {
        "tipo": "avería",
        "prioridad": "alta",
        "titulo": "Calentador de agua sin funcionar y con pitido",
        "descripcion": "El cliente no tiene agua caliente desde ayer. El calentador emite un pitido y no enciende.",
        "ubicacion": "Desconocido",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": [],
        "servicios": ["revisión de calentador", "diagnóstico de fallo"],
        "observaciones": "Urgente. Puede haber fallo electrónico o de gas."
    },
    {
        "tipo": "avería de fontanería",
        "prioridad": "alta",
        "titulo": "Tubería reventada en garaje",
        "descripcion": "El cliente informa que una tubería ha reventado en el garaje. Hay salida de agua a presión.",
        "ubicacion": "garaje",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": ["tubería", "abrazaderas", "cinta selladora"],
        "servicios": ["reparación de tuberías"],
        "observaciones": "Urgente. Posible riesgo de inundación. Cortar agua si es posible."
    },
    {
        "tipo": "solicitud de servicio",
        "prioridad": "baja",
        "titulo": "Instalación de punto de recarga para coche eléctrico",
        "descripcion": "El cliente consulta si se puede instalar un punto de recarga para coche eléctrico en su aparcamiento.",
        "ubicacion": "aparcamiento",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": ["punto de recarga", "cableado eléctrico"],
        "servicios": ["instalación eléctrica"],
        "observaciones": "Solicita información técnica y presupuesto."
    },
    {
        "tipo": "consulta técnica",
        "prioridad": "baja",
        "titulo": "Consulta sobre cambio de iluminación a sensores de movimiento",
        "descripcion": "El cliente pregunta si es posible cambiar la iluminación del pasillo a sensores de movimiento.",
        "ubicacion": "pasillo",
        "cliente": {
            "nombre": "Desconocido", "nif": None, "email": None
        },
        "materiales": ["sensor de movimiento", "luminarias LED"],
        "servicios": ["instalación de sensores"],
        "observaciones": "Evaluar viabilidad técnica y coste de implementación."
    }
]

# Inserta cada mensaje
for m in mensajes:
    cursor.execute('''
        INSERT INTO mensajes_clientes (
            tipo, prioridad, titulo, descripcion, ubicacion,
            cliente_nombre, cliente_nif, cliente_email,
            materiales, servicios, observaciones
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        m["tipo"],
        m["prioridad"],
        m["titulo"],
        m["descripcion"],
        m["ubicacion"],
        m["cliente"]["nombre"],
        m["cliente"]["nif"],
        m["cliente"]["email"],
        json.dumps(m["materiales"], ensure_ascii=False),
        json.dumps(m["servicios"], ensure_ascii=False),
        m["observaciones"]
    ))

conn.commit()
conn.close()
print("✔ Mensajes insertados correctamente.")
