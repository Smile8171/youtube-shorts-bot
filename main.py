import os
import json
import time
from google import genai
from gtts import gTTS
from moviepy import TextClip, AudioFileClip, concatenate_videoclips, ColorClip, CompositeVideoClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def generate_short_content():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY_1"))
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="Generate a catchy Title, Hook, and Short Body (under 50 words) for a YouTube Short about amazing coding tips or tech facts. Format clearly with 'Title:', 'Hook:', and 'Body:'."
    )
    text = response.text
    print("Generated Content:\n", text)
    return text

def create_video(text, output_filename="output.mp4"):
    tts = gTTS(text=text, lang='en', slow=False)
    audio_path = "voiceover.mp3"
    tts.save(audio_path)
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    bg_clip = ColorClip(size=(1080, 1920), color=(20, 20, 20), duration=duration)
    txt_clip = TextClip(text=text, font_size=50, color='white', size=(900, 1500), method='caption')
    txt_clip = txt_clip.with_duration(duration).with_position('center')

    final_video = CompositeVideoClip([bg_clip, txt_clip])
    final_video = final_video.with_audio(audio_clip)
    
    final_video.write_videofile(output
