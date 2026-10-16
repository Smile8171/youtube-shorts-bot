import os
import time
import google.genai as genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

# 5 alag-alag API keys
API_KEYS = [
    os.environ.get("GEMINI_API_KEY_1"),
    os.environ.get("GEMINI_API_KEY_2"),
    os.environ.get("GEMINI_API_KEY_3"),
    os.environ.get("GEMINI_API_KEY_4"),
    os.environ.get("GEMINI_API_KEY_5")
]

def generate_script_and_prompts():
    prompt = """
    Create an engaging YouTube Short script about interesting tech or science facts.
    Provide the output in valid JSON format with keys: title, hook, body, call_to_action, and visual_prompts.
    """
    
    valid_keys = [k for k in API_KEYS if k]
    if not valid_keys:
        raise ValueError("Koi bhi Gemini API key set nahi hai!")

    key_index = 0
    while True:
        current_key = valid_keys[key_index % len(valid_keys)]
        client = genai.Client(api_key=current_key)
        
        try:
            print(f"Trying with API Key #{key_index + 1}...")
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
            print(f"Key #{key_index + 1} failed: {e}")
            key_index += 1
            print("Switching to next API key...")
            time.sleep(3)

if __name__ == "__main__":
    data = generate_script_and_prompts()
    print(data)
