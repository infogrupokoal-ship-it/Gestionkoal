# temp_send_whatsapp.py
from backend import create_app
from backend.whatsapp import WhatsAppClient

def send_message():
    app = create_app()
    with app.app_context():
        try:
            client = WhatsAppClient()
            # El número de teléfono debe estar en formato internacional sin el '+' o espacios.
            # Asumimos que el número de España (+34) se formatea como '34XXXXXXXXX'.
            phone_number = "34633660438"
            message = (
                "Hola, te contactamos desde Grupo Koal. Este es un mensaje de prueba para "
                "verificar la integración de nuestro nuevo sistema de gestión de avisos y "
                "profesionales. ¡El sistema de notificaciones por WhatsApp funciona "
                "correctamente! Un saludo."
            )
            
            print(f"Intentando enviar a: {phone_number}")
            print(f"Mensaje: {message}")
            
            response = client.send_text(phone_number, message)
            
            print("Respuesta del cliente de WhatsApp:")
            print(response)
            
            if response.get("ok"):
                print("\nÉxito: El mensaje fue procesado por el cliente.")
            else:
                print(f"\nError: {response.get('error', 'Error desconocido.')}")

        except Exception as e:
            print(f"Ocurrió una excepción al intentar enviar el mensaje: {e}")

if __name__ == "__main__":
    send_message()
