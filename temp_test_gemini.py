import os

import google.generativeai as genai

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables.")
    exit()

genai.configure(api_key=GEMINI_API_KEY)

def test_gemini_model():
    # print("Listing available Gemini models:")
    # for m in genai.list_models():
    #     if "generateContent" in m.supported_generation_methods:
    #         print(m.name)
    # print("Test successful!")

    # Simple prompt to test connectivity and response
    model = genai.GenerativeModel("models/gemini-flash-latest") # Or "gemini-pro"
    prompt = "Hello, Gemini!"
    print(f"Sending prompt: {prompt}")
    response = model.generate_content(prompt)

    print("Gemini response:")
    print(response.text)
    print("Test successful!")

if __name__ == "__main__":
    test_gemini_model()
