import os
import json
import time
import random
import asyncio
import urllib.parse
import requests
import edge_tts
from PIL import Image
from google import genai
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# 1. FIXED CHARACTER DESIGN
CHARACTER_LOCK = (
    "3D Pixar Disney style Indian cartoon animation, featuring two exact consistent characters: "
    "Golu (a chubby cheerful Indian boy with a thick black mustache wearing a bright red kurta and white pajama) "
    "and Pappu (a tall thin clumsy Indian boy wearing round glasses, a yellow t-shirt, and blue jeans), "
)

# 2. DAILY RANDOM TOPICS
STORY_TOPICS = [
    "free samosa competition in the market",
    "funny ghost rumor in an old haveli at night",
    "broken scooter repair desi jugaad gone wrong",
    "chased by an angry street bull after wearing red",
    "trying to catch a smart monkey who stole Golu's lunchbox",
    "opening a chaotic roadside chai stall",
    "lottery ticket confusion and funny celebration",
    "hiding from the strict landlord on rent day",
    "magic potion from a fake baba that causes hiccups",
    "cricket match where the ball breaks the neighbor's window",
    "flying a giant kite that lifts Pappu into the air",
    "fake treasure map found in the backyard"
]

def generate_short_content():
    chosen_topic = random.choice(STORY_TOPICS)
    prompt = f"""
    Create a hilarious, high-energy Indian cartoon comedy story for a YouTube Short (35-45 words) in Hindi (Devanagari script) about our two fixed best friend characters: 'गोलू' (Golu - who loves food/samosas) and 'पप्पू' (Pappu - who makes funny clumsy ideas).
    Today's unique episode topic is: {chosen_topic}.
    Make sure the story is completely fresh, funny, and ends with a punchline.

    Return ONLY valid JSON in this exact format (no markdown, no extra text):
    {{
      "title": "Funny Catchy Hindi Title with Golu & Pappu #Shorts #Cartoon",
      "narration": "चटपटी और मजेदार हिंदी कहानी जिसमें गोलू और पप्पू का नाम हो (सिर्फ बोलने वाला टेक्स्ट, कोई इमोजी या स्टार नहीं)।",
      "scene_actions": [
        "standing in a colorful Indian bazaar looking excited at a samosa shop, bright morning lighting",
        "doing a funny comical action related to the story, exaggerated cartoon expressions, dynamic angle",
        "laughing together in a hilarious ending scene, vibrant colors, cinematic 3D lighting"
      ]
    }}
    """

    # Aapki saari API keys aur backup models ki list
    api_keys = [
        os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        for i in range(1, 6)
        if os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
    ]
    models_to_try = ["gemini-3.8-flash", "gemini-2.5-pro", "gemini-2.0-flash"]

    for model_name in models_to_try:
        for idx, key in enumerate(api_keys):
            try:
                print(f"Trying {model_name} with API Key #{idx + 1}...")
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                data = json.loads(raw)
                print("Generated Episode:\n", json.dumps(data, ensure_ascii=False, indent=2))
                return data
            except Exception as e:
                print(f"Warning on {model_name} (Key #{idx + 1}): {e}. Retrying in 5s...")
                time.sleep(5)

    raise RuntimeError("Saare Gemini models/keys abhi busy hain!")

async def make_hindi_voice(text, output_file="voiceover.mp3"):
    communicate = edge_tts.Communicate(
        text=text,
        voice="hi-IN-MadhurNeural",
        rate="+12%",
        pitch="+15Hz"
    )
    await communicate.save(output_file)

def download_cartoon_image(scene_action, filename):
    full_prompt = f"{CHARACTER_LOCK} {scene_action}, vibrant colors, high quality 3D render, vertical 9:16"
    encoded = urllib.parse.quote(full_prompt)
    fixed_seed = 424242
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={fixed_seed}&nologo=true"
    
    print(f"Generating consistent character scene: {filename}...")
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(filename, "wb") as f:
                    f.write(resp.content)
                return filename
        except Exception as e:
            print(f"Retry {attempt + 1} for {filename}: {e}")
            
    img = Image.new("RGB", (1080, 1920), color=(255, 140, 0))
    img.save(filename)
    return filename

def create_video(data, output_filename="output.mp4"):
    audio_path = "voiceover.mp3"
    asyncio.run(make_hindi_voice(data["narration"], audio_path))

    audio_clip = AudioFileClip(audio_path)
    total_duration = audio_clip.duration

    scenes = data.get("scene_actions", [])
    clip_duration = total_duration / len(scenes)

    image_clips = []
    for i, action in enumerate(scenes):
        img_path = download_cartoon_image(action, f"scene_{i}.jpg")
        clip = ImageClip(img_path).with_duration(clip_duration)
        image_clips.append(clip)

    final_video = concatenate_videoclips(image_clips, method="compose")
    final_video = final_video.with_audio(audio_clip)

    final_video.write_videofile(output_filename, fps=24, codec='libx264', audio_codec='aac')

    audio_clip.close()
    final_video.close()
    return output_filename

def upload_to_youtube(video_path, title):
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_sec = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

    if not client_id or not client_sec or not refresh_token:
        print("Error: YouTube credentials missing hain!")
        return

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_sec
    )

    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {
            "title": title[:100],
            "description": "Golu aur Pappu ki Nayi Kahani! #Shorts #Cartoon #HindiKahani #Comedy",
            "tags": ["Shorts", "HindiCartoon", "GoluPappu", "Animation", "FunnyShorts"],
            "categoryId": "24"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    print(f"Uploading '{title}' to YouTube...")

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    print(f"Successfully uploaded! Video ID: {response.get('id')}")

if __name__ == "__main__":
    data = generate_short_content()
    video_file = create_video(data)
    upload_to_youtube(video_file, data["title"])
