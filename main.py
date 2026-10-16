import os
import time
import google.genai as genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_script_and_prompts():
    prompt = """
    Create an engaging YouTube Short script about interesting tech or science facts.
    Provide the output in valid JSON format with keys: title, hook, body, call_to_action, and visual_prompts.
    """
    
    attempt = 1
    while True:
        try:
            print(f"Attempt {attempt}: Generating YouTube Short script...")
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            )
            print("Generated successfully!")
            return response.text
        except (ServerError, ClientError) as e:
            # Agar 503 ya koi temporary error ho toh 10 second ruk kar dobara try karega
            print(f"Error encountered: {e}. Retrying in 10 seconds...")
            time.sleep(10)
            attempt += 1

if __name__ == "__main__":
    data = generate_script_and_prompts()
    print(data)
