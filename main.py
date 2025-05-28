from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid
from langdetect import detect
import edge_tts
import librosa
import numpy as np
import soundfile as sf
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Allow frontend on port 8080
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supported languages (mapped to Edge TTS locales)
SUPPORTED_LANGUAGES = ["en-US", "es-ES", "fr-FR", "de-DE", "zh-CN", "hi-IN"]

class TTSRequest(BaseModel):
    text: str
    language: str = ""
    voice: str = "en-US-JennyNeural"

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    text = request.text.strip()
    language = request.language
    voice = request.voice

    # Validate text length
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Detect language if not provided
    if not language:
        try:
            detected_lang = detect(text)
            # Map detected language to Edge TTS locale
            lang_map = {
                "en": "en-US",
                "es": "es-ES",
                "fr": "fr-FR",
                "de": "de-DE",
                "zh": "zh-CN",
                "hi": "hi-IN"
            }
            language = lang_map.get(detected_lang, "en-US")
            if language not in SUPPORTED_LANGUAGES:
                language = "en-US"  # Fallback to English
        except:
            language = "en-US"  # Fallback if detection fails

    # Map voice to Edge TTS voice names
    voice_map = {
        "en-US-AriaNeural": "en-US-AriaNeural",
        "en-US-GuyNeural": "en-US-GuyNeural",
        "en-US-JennyNeural": "en-US-JennyNeural",
        "baby": "en-US-JennyNeural"  # Use Jenny for baby voice base
    }
    voice_name = voice_map.get(voice, "en-US-JennyNeural")

    # Adjust voice based on language (simplified; add more mappings as needed)
    if language != "en-US" and voice != "baby":
        voice_map = {
            "es-ES": "es-ES-ElviraNeural",
            "fr-FR": "fr-FR-DeniseNeural",
            "de-DE": "de-DE-KatjaNeural",
            "zh-CN": "zh-CN-XiaoxiaoNeural",
            "hi-IN": "hi-IN-SwaraNeural"
        }
        voice_name = voice_map.get(language, voice_name)

    # Generate unique filename
    filename = f"output_{uuid.uuid4()}.wav"
    output_path = os.path.join("audio", filename)

    # Ensure audio directory exists
    os.makedirs("audio", exist_ok=True)

    try:
        # Use Edge TTS for audio generation
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(output_path)

        # Apply pitch shift for baby voice
        if voice == "baby":
            audio, sample_rate = librosa.load(output_path)
            audio = librosa.effects.pitch_shift(audio, sr=sample_rate, n_steps=4)  # Increase pitch by 4 semitones
            sf.write(output_path, audio, sample_rate)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

    # Return audio file URL
    return {
        "audio_url": f"http://localhost:8000/audio/{filename}",
        "filename": filename
    }

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join("audio", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/wav", filename=filename)

# Cleanup old audio files (optional, can be enhanced)
@app.on_event("shutdown")
def cleanup():
    import shutil
    if os.path.exists("audio"):
        shutil.rmtree("audio")