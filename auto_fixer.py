import os
import time
from google import genai

def heal_code():
    if not os.path.exists("error.log") or not os.path.exists("main.py"):
        print("Error log ya main.py nahi mila.")
        return False

    with open("error.log", "r", encoding="utf-8") as f:
        error_log = f.read()[-4000:]  # Last 4000 chars of traceback

    with open("main.py", "r", encoding="utf-8") as f:
        current_code = f.read()

    prompt = f"""
    You are an autonomous Python Self-Healing Agent running inside GitHub Actions.
    The following `main.py` script crashed with an error.
    Analyze the traceback and fix the bug in `main.py`.
    
    IMPORTANT RULES:
    - Return ONLY the complete, runnable, fixed Python code for `main.py`.
    - Do NOT include markdown backticks (```python) or any explanation.
    - Keep all existing functionality (Gemini story generation, edge-tts Hindi voice, cartoon image generation, MoviePy v2 methods like .with_duration() and .with_audio(), and YouTube upload).

    --- TRACEBACK ERROR ---
    {error_log}

    --- CURRENT main.py ---
    {current_code}
    """

    api_keys = [
        os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        for i in range(1, 6)
        if os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
    ]
    models = ["gemini-3.8-flash", "gemini-2.5-pro", "gemini-2.0-flash"]

    for model_name in models:
        for idx, key in enumerate(api_keys):
            try:
                print(f"Auto-Fixer: Trying {model_name} (Key #{idx + 1}) to repair main.py...")
                client = genai.Client(api_key=key)
                response = client.models.generate_content(model=model_name, contents=prompt)
                fixed_code = response.text.strip()

                if fixed_code.startswith("```"):
                    fixed_code = fixed_code.split("\n", 1)[1].rsplit("```", 1)[0].strip()

                if "import " in fixed_code and "def " in fixed_code:
                    with open("main.py", "w", encoding="utf-8") as f:
                        f.write(fixed_code + "\n")
                    print("Auto-Fixer: main.py successfully repaired!")
                    return True
            except Exception as e:
                print(f"Auto-Fixer retry ({e})...")
                time.sleep(4)

    return False

if __name__ == "__main__":
    heal_code()
