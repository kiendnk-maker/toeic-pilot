# backend/pipeline.py
# 3-layer verification pipeline: dB gate → Groq Whisper STT → Cosine similarity
# Groq API key is loaded from environment variable GROQ_API_KEY

import os
import io
import tempfile
import numpy as np
import requests
from sentence_transformers import SentenceTransformer, util
import wave
import struct

# ── Config ──
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DB_THRESHOLD = 60
COSINE_THRESHOLD = 0.70

# ── Load models once at startup ──
print("[pipeline] Loading sentence-transformers model...")
_embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("[pipeline] Models loaded ✓")


def _raw_bytes_to_wav(raw_bytes: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)
    return buf.getvalue()


def check_db(audio_bytes: bytes) -> tuple:
    arr = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    if len(arr) == 0:
        return False, -999.0
    rms = np.sqrt(np.mean(arr ** 2))
    db = 20 * np.log10(rms + 1e-9)
    return db >= DB_THRESHOLD, round(db, 1)


def transcribe_groq(audio_bytes: bytes) -> str:
    try:
        header = audio_bytes[:12]
        is_raw = not (header.startswith(b'RIFF') or header.startswith(b'\x1aE\xdf\xa3') or header.startswith(b'ID3') or header.startswith(b'\xff\xfb') or header.startswith(b'OggS'))
    except Exception:
        is_raw = True

    if is_raw:
        audio_bytes = _raw_bytes_to_wav(audio_bytes, sample_rate=16000, channels=1, sample_width=2)

    files = {'file': ('audio.wav', audio_bytes, 'audio/wav')}
    data = {
        'model': 'whisper-large-v3-turbo',
        'response_format': 'json',
        'language': 'en',
        'temperature': 0.0
    }
    headers = {'Authorization': f'Bearer {GROQ_API_KEY}'}
    resp = requests.post(GROQ_TRANSCRIPTION_URL, files=files, data=data, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    return result.get('text', '').strip()


def check_similarity(hypothesis: str, reference: str) -> float:
    emb1 = _embedder.encode(hypothesis, convert_to_tensor=True)
    emb2 = _embedder.encode(reference, convert_to_tensor=True)
    return float(util.cos_sim(emb1, emb2))


def verify_audio(audio_bytes: bytes, reference: str) -> dict:
    db_pass, db_val = check_db(audio_bytes)
    if not db_pass:
        return {
            "db_pass": False, "stt_text": "", "cosine_score": 0.0,
            "passed": False, "bypass_used": False,
            "message": f"🔊 Please speak louder! ({db_val} dB < {DB_THRESHOLD} dB)"
        }
    try:
        stt_text = transcribe_groq(audio_bytes)
    except Exception as e:
        return {
            "db_pass": True, "stt_text": "", "cosine_score": 0.0,
            "passed": False, "bypass_used": False,
            "message": f"⚠️ STT error: {str(e)[:80]}"
        }
    if not stt_text:
        return {
            "db_pass": True, "stt_text": "", "cosine_score": 0.0,
            "passed": False, "bypass_used": False,
            "message": "🤔 Could not understand. Please speak clearly and try again."
        }
    cosine = check_similarity(stt_text, reference)
    passed = cosine >= COSINE_THRESHOLD
    return {
        "db_pass": True,
        "stt_text": stt_text,
        "cosine_score": round(cosine, 3),
        "passed": passed,
        "bypass_used": False,
        "message": f"✅ Correct! ({cosine:.2f})" if passed else f"❌ Try again — similarity {cosine:.2f} (need ≥ {COSINE_THRESHOLD})"
    }