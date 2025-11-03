import json

def validate_message(message, index):
    errors = []

    # 1. Campos obligatorios
    required_fields = ["tipo", "prioridad", "titulo", "descripcion", "ubicacion", "cliente", "materiales", "servicios", "observaciones"]
    for field in required_fields:
        if field not in message or message[field] is None or (isinstance(message[field], str) and not message[field].strip()):
            errors.append(f"Falta campo obligatorio o está vacío: '{field}'")

    # 2. Validación de tipos y valores
    if "tipo" in message and not isinstance(message["tipo"], str):
        errors.append(f"Tipo de dato incorrecto para 'tipo': {type(message["tipo"]).__name__}")
    
    if "prioridad" in message:
        if not isinstance(message["prioridad"], str):
            errors.append(f"Tipo de dato incorrecto para 'prioridad': {type(message["prioridad"]).__name__}")
        elif message["prioridad"].lower() not in ["alta", "media", "baja"]:
            errors.append(f"Valor no válido para 'prioridad': '{message["prioridad"]}'. Valores permitidos: alta, media, baja.")

    if "titulo" in message and not isinstance(message["titulo"], str):
        errors.append(f"Tipo de dato incorrecto para 'titulo': {type(message["titulo"]).__name__}")

    if "descripcion" in message and not isinstance(message["descripcion"], str):
        errors.append(f"Tipo de dato incorrecto para 'descripcion': {type(message["descripcion"]).__name__}")

    if "ubicacion" in message and not isinstance(message["ubicacion"], str):
        errors.append(f"Tipo de dato incorrecto para 'ubicacion': {type(message["ubicacion"]).__name__}")

    # 3. Estructura anidada 'cliente'
    if "cliente" in message:
        if not isinstance(message["cliente"], dict):
            errors.append(f"Tipo de dato incorrecto para 'cliente': {type(message["cliente"]).__name__}. Se esperaba un objeto.")
        elif "nombre" not in message["cliente"] or not message["cliente"]["nombre"]:
            errors.append("Campo obligatorio 'cliente.nombre' falta o está vacío.")
        # Puedes añadir más validaciones para nif y email si son obligatorios o tienen un formato específico

    # 4. Estructura 'materiales' (debe ser una lista de objetos)
    if "materiales" in message:
        if not isinstance(message["materiales"], list):
            errors.append(f"Tipo de dato incorrecto para 'materiales': {type(message["materiales"]).__name__}. Se esperaba una lista.")
        else:
            for i, material in enumerate(message["materiales"]):
                if not isinstance(material, dict):
                    errors.append(f"Elemento {i} en 'materiales' tiene tipo incorrecto: {type(material).__name__}. Se esperaba un objeto.")
                # Puedes añadir validaciones para los campos dentro de cada material

    # 5. Estructura 'servicios' (debe ser una lista de strings)
    if "servicios" in message:
        if not isinstance(message["servicios"], list):
            errors.append(f"Tipo de dato incorrecto para 'servicios': {type(message["servicios"]).__name__}. Se esperaba una lista.")
        else:
            for i, servicio in enumerate(message["servicios"]):
                if not isinstance(servicio, str):
                    errors.append(f"Elemento {i} en 'servicios' tiene tipo incorrecto: {type(servicio).__name__}. Se esperaba un string.")

    return errors

if __name__ == "__main__":
    file_path = "mock_error_messages.json"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            mock_error_messages = json.load(f)
    except FileNotFoundError:
        print(f"Error: El archivo '{file_path}' no se encontró.")
        exit()
    except json.JSONDecodeError:
        print(f"Error: El archivo '{file_path}' no es un JSON válido.")
        exit()

    print(f"\n--- Validando {len(mock_error_messages)} mensajes con errores intencionales ---")
    for i, message in enumerate(mock_error_messages):
        validation_errors = validate_message(message, i)
        if validation_errors:
            print(f"[❌] Mensaje {i+1}: {message.get('titulo', 'Sin título')}")
            for error in validation_errors:
                print(f"    - {error}")
        else:
            print(f"[✅] Mensaje {i+1}: {message.get('titulo', 'Sin título')} (inesperadamente válido)")
    print("\n--- Validación completada ---")
