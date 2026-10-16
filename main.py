import os
import google.genai as genai
from google.genai import types

# Initialize client using environment variable GEMINI_API_KEY
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_script_and_prompts():
    prompt = """
    Create an engaging YouTube Short script about interesting tech or science facts.
    Provide the output in valid JSON format with keys: title, hook, body, call_to_action, and visual_prompts.
    """
    
    # Fix: Use application/json or text/plain for response_mime_type
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    return response.text

if __name__ == "__main__":
    print("Generating YouTube Short script...")
    data = generate_script_and_prompts()
    print("Generated successfully!")
    print(data)
