import os
import io
import json
import time
import random
import asyncio
import urllib.parse
import requests
import edge_tts
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont
from google import genai
from moviepy import VideoClip, AudioFileClip, concatenate_videoclips
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

CHAR_STYLE = "3D Pixar cartoon Indian comedy, chubby boy Golu in red kurta with mustache and thin boy Pappu in yellow shirt with glasses,"

STORY_TOPICS = [
    "free samosa eating competition in market",
    "funny ghost prank in old haveli at night",
    "flying a giant kite that lifts Pappu in the air",
    "chased by a funny street dog after stealing laddoos",
    "desi jugaad cooler invention explodes with water",
    "trying to catch a naughty monkey who took Golu's samosa",
    "cricket ball breaks strict neighbor's window",
    "funny confusion with a lottery ticket"
]

def get_gemini_api_keys():
    keys = []
    default_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if default_key:
        keys.append(default_key)
    for i in range(1, 10):
        k = os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys

def generate_short_content():
    chosen_topic = random.choice(STORY_TOPICS)
    prompt = f"""
    Create a fast-paced, hilarious Indian cartoon YouTube Short script (40-50 words) in Hindi (Devanagari) about Golu (गोलू) and Pappu (पप्पू).
    Topic: {chosen_topic}.
    Split the story into EXACTLY 6 fast scenes so the video has great editing.

    Return ONLY valid JSON in this exact format (no markdown, no extra text):
    {{
      "title": "Funny Catchy Hindi Title #Shorts #Cartoon",
      "scenes": [
        {{"line": "पहली मजेदार लाइन।", "visual": "Golu and Pappu standing in colorful Indian market looking excited"}},
        {{"line": "दूसरी मजेदार लाइन।", "visual": "Pappu showing a funny crazy idea with hand gestures"}},
        {{"line": "तीसरी लाइन में कुछ गड़बड़ होती है।", "visual": "funny chaos action scene with shocked cartoon expressions"}},
        {{"line": "चौथी लाइन में दोनों भागते हैं।", "visual": "both running comically in panic through Indian street"}},
        {{"line": "पांचवीं लाइन में मजेदार मोड़।", "visual": "Golu doing something clumsy and funny, vibrant 3D lighting"}},
        {{"line": "आखिर में एक धमाकेदार पंचलाइन!", "visual": "both laughing hysterically in a funny ending pose"}}
      ]
    }}
    """

    api_keys = get_gemini_api_keys()
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-pro"]

    for model_name in models_to_try:
        for idx, key in enumerate(api_keys):
            try:
                print(f"Trying {model_name} with Key #{idx + 1}...")
                client = genai.Client(api_key=key)
                response = client.models.generate_content(model=model_name, contents=prompt)
                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                return json.loads(raw)
            except Exception as e:
                print(f"Retry ({e})...")
                time.sleep(2)

    raise RuntimeError("All Gemini keys busy!")

async def make_hindi_voice(text, output_file):
    communicate = edge_tts.Communicate(
        text=text,
        voice="hi-IN-MadhurNeural",
        rate="+15%",
        pitch="+15Hz"
    )
    await communicate.save(output_file)

def create_fallback_cartoon_image(filename, visual_prompt=""):
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), color=(255, 140, 0))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        ratio = y / h
        r = int(255 - ratio * 80)
        g = int(140 + ratio * 40)
        b = int(30 + ratio * 180)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Bright cartoon sun / lighting glow
    draw.ellipse([w // 2 - 280, int(h * 0.12), w // 2 + 280, int(h * 0.12) + 560], fill=(255, 235, 120))
    draw.ellipse([w // 2 - 240, int(h * 0.12) + 40, w // 2 + 240, int(h * 0.12) + 520], fill=(255, 250, 180))

    # Cartoon ground / stage
    draw.rectangle([0, int(h * 0.72), w, h], fill=(60, 30, 90))
    draw.rectangle([0, int(h * 0.70), w, int(h * 0.72)], fill=(255, 90, 140))

    # Comic title box
    box_top = int(h * 0.44)
    box_bottom = int(h * 0.58)
    draw.rectangle([80, box_top, w - 80, box_bottom], fill=(20, 20, 40))
    draw.rectangle([90, box_top + 10, w - 90, box_bottom - 10], outline=(255, 215, 0), width=6)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    draw.text((w // 2 - 130, int(h * 0.49)), "GOLU & PAPPU", fill=(255, 235, 50), font=font)
    draw.text((w // 2 - 100, int(h * 0.52)), "HINDI COMEDY", fill=(255, 255, 255), font=font)

    img.save(filename, quality=95)
    return filename

def try_download_image(url, filename, headers):
    resp = requests.get(url, headers=headers, timeout=25)
    if resp.status_code == 200 and len(resp.content) > 3000:
        content_type = resp.headers.get("Content-Type", "")
        if "image" in content_type or resp.content[:4] in [b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"\x89PNG", b"RIFF"]:
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
            img.save(filename, quality=95)
            return True
    return False

def download_real_cartoon_image(visual_prompt, filename, scene_idx, prev_image=None):
    clean_prompt = f"{CHAR_STYLE} {visual_prompt}, vibrant 3D Pixar render, vertical 9:16"
    encoded_full = urllib.parse.quote(clean_prompt)
    encoded_short = urllib.parse.quote(f"3D Pixar cartoon Golu and Pappu, {visual_prompt}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
    }

    urls_to_try = [
        f"https://image.pollinations.ai/prompt/{encoded_full}?width=720&height=1280&model=turbo&seed={1000 + scene_idx}&nologo=true",
        f"https://image.pollinations.ai/prompt/{encoded_short}?width=720&height=1280&model=turbo&seed={random.randint(1, 99999)}&nologo=true",
        f"https://image.pollinations.ai/prompt/{encoded_full}?width=540&height=960&nologo=true&seed={42424 + scene_idx}",
        f"https://image.pollinations.ai/prompt/{encoded_short}?width=720&height=1280&nologo=true"
    ]

    for attempt, url in enumerate(urls_to_try):
        try:
            time.sleep(1 if attempt == 0 else 3)
            print(f"Downloading Scene {scene_idx + 1} (Attempt {attempt + 1})...")
            if try_download_image(url, filename, headers):
                print(f"Scene {scene_idx + 1} downloaded successfully!")
                return filename
        except Exception as e:
            print(f"Image retry {attempt + 1} warning: {e}")

    # Fallback 1: Re-use and transform previous cartoon scene if available
    if prev_image and os.path.exists(prev_image):
        print(f"Using smart flipped closeup of previous cartoon scene for Scene {scene_idx + 1}...")
        img = Image.open(prev_image).convert("RGB")
        img = ImageOps.mirror(img)
        w, h = img.size
        cropped = img.crop((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)))
        cropped.resize((1080, 1920), Image.Resampling.LANCZOS).save(filename, quality=95)
        return filename

    # Fallback 2: Generate guaranteed high-quality cartoon frame so pipeline never crashes
    print(f"Using cartoon visual frame for Scene {scene_idx + 1}...")
    create_fallback_cartoon_image(filename, visual_prompt)
    return filename

def make_zoom_clip(image_path, duration, zoom_in=True):
    base_img = Image.open(image_path).convert("RGB")
    w, h = base_img.size

    def make_frame(t):
        progress = t / max(duration, 0.1)
        scale = (1.0 + 0.16 * progress) if zoom_in else (1.16 - 0.16 * progress)
        crop_w, crop_h = int(w / scale), int(h / scale)
        left = (w - crop_w) // 2
        top = (h - crop_h) // 2
        cropped = base_img.crop((left, top, left + crop_w, top + crop_h))
        resized = cropped.resize((w, h), Image.Resampling.BILINEAR)
        return np.array(resized)

    return VideoClip(make_frame).with_duration(duration)

def create_video(data, output_filename="output.mp4"):
    scenes = data.get("scenes", [])
    final_clips = []
    last_valid_img = None

    for i, scene in enumerate(scenes):
        audio_file = f"voice_{i}.mp3"
        asyncio.run(make_hindi_voice(scene["line"], audio_file))
        audio_clip = AudioFileClip(audio_file)
        dur = audio_clip.duration

        img_file = download_real_cartoon_image(scene["visual"], f"scene_{i}.jpg", i, last_valid_img)
        last_valid_img = img_file

        video_clip = make_zoom_clip(img_file, dur, zoom_in=(i % 2 == 0))
        video_clip = video_clip.with_audio(audio_clip)
        final_clips.append(video_clip)

    final_video = concatenate_videoclips(final_clips, method="compose")
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac")
    final_video.close()
    return output_filename

def upload_to_youtube(video_path, title):
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_sec = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

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
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

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
