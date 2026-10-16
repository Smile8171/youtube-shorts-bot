import os
import random
import requests
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Moviepy version compatibility import
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

import edge_tts
import asyncio
import json

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

def generate_script_and_prompts():
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = """
    Ek 45-second ka rochak Hindi YouTube Short script likho.
    Pehli line ekdam shocking ya unbelievable fact hona chahiye (Viral Hook).
    Bhasha aisi ho jo bolne mein natural lage (Hinglish/Simple Hindi).
    Mujhe JSON format mein response do jismein:
    1. "title": Short ka catchy title aur hashtag (#Shorts).
    2. "description": SEO description aur tags.
    3. "script_text": Poora bolne wala text (bina kisi heading ke).
    4. "visual_prompts": 4 alag-alag cinematic AI image prompts English mein.
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="json"),
    )
    return json.loads(response.text)

async def create_voiceover(text):
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    audio_path = "voiceover.mp3"
    await communicate.save(audio_path)
    return audio_path

def download_images(prompts):
    image_paths = []
    for i, prompt in enumerate(prompts):
        clean_prompt = prompt.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1080&height=1920&nologo=true"
        response = requests.get(url)
        if response.status_code == 200:
            path = f"img_{i}.jpg"
            with open(path, "wb") as f:
                f.write(response.content)
            image_paths.append(path)
    return image_paths

def create_video(image_paths, audio_path):
    audio_clip = AudioFileClip(audio_path)
    total_duration = audio_clip.duration
    clip_duration = total_duration / len(image_paths)
    clips = []
    for path in image_paths:
        img_clip = ImageClip(path).set_duration(clip_duration)
        if hasattr(img_clip, 'resize'):
            img_clip = img_clip.resize(height=1920)
        else:
            img_clip = img_clip.resized(height=1920)
        img_clip = img_clip.set_fps(24)
        clips.append(img_clip)
    video = concatenate_videoclips(clips, method="compose").set_audio(audio_clip)
    output_path = "final_output.mp4"
    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    return output_path

def upload_to_youtube(video_path, title, description):
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title,
            "description": description + "\n\n#Shorts #Viral #Trending",
            "tags": ["shorts", "hindi shorts", "viral facts", "automation"],
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
    print("Video successfully uploaded!")

if __name__ == "__main__":
    data = generate_script_and_prompts()
    audio_file = asyncio.run(create_voiceover(data["script_text"]))
    img_files = download_images(data["visual_prompts"])
    vid_file = create_video(img_files, audio_file)
    upload_to_youtube(vid_file, data["title"], data["description"])
