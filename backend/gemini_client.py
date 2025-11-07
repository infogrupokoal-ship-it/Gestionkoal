# backend/gemini_client.py
import google.generativeai as genai
from flask import current_app

# This module will now handle the Gemini client initialization and generation.


def get_model():
    """
    Initializes and returns a Gemini GenerativeModel instance based on app config.
    """
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        current_app.logger.error("GEMINI_API_KEY not configured.")
        return None

    try:
        genai.configure(api_key=api_key)
        model_name = current_app.config.get("GEMINI_MODEL", "models/gemini-pro-latest")
        model = genai.GenerativeModel(model_name)
        return model
    except Exception as e:
        current_app.logger.error(f"Failed to initialize Gemini model: {e}")
        return None


def generate_text_from_prompt(prompt_text: str) -> str:
    """
    Generates a text response from a single, non-chat prompt.
    """
    model = get_model()
    if model is None:
        raise ValueError("El cliente de IA no está configurado correctamente.")

    try:
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        current_app.logger.error(f"Error calling Gemini API (generate_content): {e}")
        raise e

def generate_chat_response(
    history: list[dict], user_message: str, system_instruction: str
) -> str:
    """
    Generates a conversational response from Gemini using a chat history.
    """
    model = get_model()
    if model is None:
        return "Error: El cliente de IA no está configurado correctamente."

    # The system instruction is now passed with the model initialization for some versions,
    # but for conversational chat, it's better to prepend it to the history if not native.
    # For simplicity and compatibility, we will start a new chat with the history.
    model.system_instruction = system_instruction
    chat = model.start_chat(history=history)

    try:
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        current_app.logger.error(f"Error calling Gemini API: {e}")
        return (
            f"Lo siento, ha ocurrido un error al contactar con el servicio de IA: {e}"
        )
