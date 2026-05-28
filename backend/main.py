# backend/main.py
# FastAPI app — TOEIC Active Recall Pilot System
# Endpoints: /api/verify, /api/verify-text, /api/session/complete,
#            /api/test/submit, /api/admin/export, /api/admin/metrics

import time
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from pipeline import verify_audio
from database import (
    log_session, log_attempt, log_test_score,
    export_csv, get_feasibility_metrics,
)
from questions import router as questions_router

app = FastAPI(title="TOEIC Active Recall Pilot")

# CORS — allow all origins for localhost dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── TTS Endpoint (edge-tts) ──
@app.get("/api/tts")
async def text_to_speech(text: str):
    """
    Generate audio for the given text using edge-tts.
    Returns MP3 audio file.
    """
    import subprocess, os, uuid, asyncio

    # Sanitize: strip HTML tags, limit length
    text = text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
    text = text.replace("*", "")  # remove markdown markers
    if len(text) > 500:
        text = text[:500]

    tmp_path = f"/tmp/tts_{uuid.uuid4().hex}.mp3"
    try:
        proc = await asyncio.create_subprocess_exec(
            "edge-tts",
            "--text", text,
            "--voice", "en-US-EmmaMultilingualNeural",
            "--write-media", tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if not os.path.exists(tmp_path):
            return {"error": "TTS generation failed"}
        from fastapi.responses import FileResponse
        return FileResponse(tmp_path, media_type="audio/mpeg", filename="tts.mp3")
    except Exception as e:
        return {"error": str(e)}


# ── Mount static frontend ──
app.mount("/static", StaticFiles(directory="../frontend", html=True), name="static")

# ── Include questions router ──
app.include_router(questions_router)


@app.get("/")
async def root():
    return HTMLResponse('<meta http-equiv="refresh" content="0;url=/static/index.html">')


# ── Core Verification Endpoint ──
@app.post("/api/verify")
async def verify(
    audio: UploadFile = File(...),
    reference: str = Form(...),
    participant_id: str = Form("P000"),
    question_id: str = Form("Q00"),
    attempt_num: int = Form(1),
):
    """
    Main 3-layer pipeline endpoint.
    Receives audio blob → runs dB gate → Groq Whisper → cosine similarity.
    Logs all data to SQLite.
    """
    t0 = time.time()
    audio_bytes = await audio.read()

    if len(audio_bytes) == 0:
        return {"passed": False, "db_pass": False, "stt_text": "", "cosine_score": 0.0,
                "latency_ms": 0, "message": "⚠️ No audio received."}

    result = verify_audio(audio_bytes, reference)
    latency_ms = int((time.time() - t0) * 1000)

    # Log to database
    try:
        log_attempt(
            participant_id=participant_id,
            question_id=question_id,
            attempt_num=attempt_num,
            db_pass=result["db_pass"],
            stt_text=result["stt_text"],
            cosine_score=result["cosine_score"],
            passed=result["passed"],
            bypass_used=result.get("bypass_used", False),
            latency_ms=latency_ms,
        )
    except Exception as e:
        print(f"[WARN] DB log failed: {e}")

    return {
        "passed": result["passed"],
        "db_pass": result["db_pass"],
        "stt_text": result["stt_text"],
        "cosine_score": result["cosine_score"],
        "latency_ms": latency_ms,
        "message": result["message"],
    }


# ── Text-based Verification (Bypass) ──
@app.post("/api/verify-text")
async def verify_text(
    text: str = Form(...),
    reference: str = Form(...),
    participant_id: str = Form("P000"),
    question_id: str = Form("Q00"),
):
    """
    Bypass mode: typed text instead of voice.
    Runs only cosine similarity (no dB gate or STT).
    """
    from pipeline import check_similarity, COSINE_THRESHOLD

    score = check_similarity(text, reference)
    passed = score >= COSINE_THRESHOLD

    log_attempt(
        participant_id=participant_id,
        question_id=question_id,
        attempt_num=3,  # bypass = attempt 3
        db_pass=True,
        stt_text=text,
        cosine_score=score,
        passed=passed,
        bypass_used=True,
        latency_ms=0,
    )

    return {
        "passed": passed,
        "cosine_score": round(score, 3),
        "message": (
            f"✅ Correct! ({score:.2f})"
            if passed
            else            f"❌ Similarity {score:.2f} (need ≥ {COSINE_THRESHOLD})"
        ),
    }


# ── Session Completion ──
@app.post("/api/session/complete")
async def complete_session(data: dict):
    """
    Called when a participant finishes a daily 10-question session.
    """
    log_session(
        participant_id=data.get("participant_id", "P000"),
        day=data.get("day", 1),
        scores=data.get("scores", {}),
    )
    return {"status": "ok"}


# ── Test Score Submission ──
@app.post("/api/test/submit")
async def submit_test(data: dict):
    """
    Submit pre-test or post-test scores.
    """
    log_test_score(
        participant_id=data.get("participant_id", "P000"),
        group_type=data.get("group_type", ""),
        test_type=data.get("test_type", "pretest"),
        score=data.get("score", 0),
        total=data.get("total", 30),
    )
    return {"status": "ok"}


# ── Admin Endpoints ──
@app.get("/api/admin/export")
async def admin_export():
    """Export all data as JSON (for admin dashboard)."""
    return export_csv()


@app.get("/api/admin/metrics")
async def admin_metrics():
    """Compute feasibility metrics from logged data."""
    return get_feasibility_metrics()


# ── Health Check ──
@app.get("/api/health")
async def health():
    return {"status": "ok", "groq_key_configured": True}


if __name__ == "__main__":
    print("[main] Starting TOEIC Active Recall Pilot server...")
    print("[main] http://localhost:8080")
    print("[main] Admin:  http://localhost:8080/static/admin.html")
    print("[main] Game:   http://localhost:8080/static/game.html?pid=P001&group=B&day=1")
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
