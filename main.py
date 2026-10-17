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
    # Step 1: Gemini API se title, hook aur body generate karna
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY_1"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Generate a catchy Title, Hook, and Short Body (under 50 words) for a YouTube Short about amazing coding tips or tech facts. Format clearly with 'Title:', 'Hook:', and 'Body:'."
    )
    text = response.text
    print("Generated Content:\n", text)
    return text

def create_video(text, output_filename="output.mp4"):
    # Step 2: Text se Audio (TTS) generate karna
    tts = gTTS(text=text, lang='en', slow=False)
    audio_path = "voiceover.mp3"
    tts.save(audio_path)
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    # Step 3: Vertical Video (Shorts format 1080x1920) banana MoviePy se
    bg_clip = ColorClip(size=(1080, 1920), color=(20, 20, 20), duration=duration)
    
    # Text overlay add karna
    txt_clip = TextClip(text, fontsize=50, color='white', size=(900, 1500), method='caption')
    txt_clip = txt_clip.set_duration(duration).set_position('center')

    # Video aur audio combine karna
    video = concatenate_videoclips([bg_clip]) # Background clip
    # Composite video banane ke liye
    from moviepy.editor import CompositeVideoClip
    final_video = CompositeVideoClip([bg_clip, txt_clip])
    final_video = final_video.set_audio(audio_clip)
    
    # Render karna
    final_video.write_videofile(output_filename, fps=24, codec='libx264', audio_codec='aac')
    
    # Cleanup temporary files
    audio_clip.close()
    final_video.close()
    return output_filename

def upload_to_youtube(video_path, title):
    # Step 4: YouTube Data API ke through upload karna
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not client_secret or not refresh_token:
        print("Error: YouTube credentials (Client Secret ya Refresh Token) missing hain!")
        return

    secret_data = json.loads(client_secret)
    client_id = secret_data.get("installed", secret_data.get("web", {})).get("client_id")
    client_sec = secret_data.get("installed", secret_data.get("web", {})).get("client_secret")

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
            "description": "Automated YouTube Short #Shorts #Coding #Tech",
            "tags": ["Shorts", "YouTubeShorts", "Coding"],
            "categoryId": "28"
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
    content = generate_short_content()
    video_file = create_video(content)
    upload_to_youtube(video_file, "Amazing Tech Tip #Shorts")
