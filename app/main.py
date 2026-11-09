"""
VoiceDose - Main Application & API Server (FastAPI)
===================================================
This file is the FastAPI entrypoint for VoiceDose:
- Serves the voice-first Patient Reminder UI and the Caregiver Dashboard.
- Connects browser audio recording to Gnani Prisma STT.
- Matches transcripts against multi-lingual intent keywords (Telugu, Hindi, Hinglish, English).
- Logs dose confirmations to SQLite.
- Generates natural spoken confirmations with Gnani Timbre TTS.

Flow per User Request:
1. Reminder spoken aloud using Gnani Timbre TTS (/api/reminder-speech).
2. User records audio response via big mic button.
3. Audio transcribed via Gnani Prisma STT and matched against intent keywords (/api/process-voice).
4. Result logged in SQLite and confirmation spoken using Timbre.
5. Caregiver page displays today's doses as taken, missed, pending, or snoozed.
"""

import base64
import logging
from urllib.parse import quote
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.config import (
    BASE_DIR,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    GNANI_API_KEY,
)
from app.database import (
    init_db,
    seed_fake_data,
    get_patient,
    get_today_doses,
    get_dose_by_id,
    get_active_dose,
    update_dose_status,
    log_voice_interaction,
    get_recent_logs,
    get_caregiver_stats,
    reset_demo_data,
)
from app.gnani_client import synthesize_speech, transcribe_audio
from app.intent_matcher import (
    match_intent,
    get_confirmation_text,
    generate_reminder_text,
)

# Configure logger
logger = logging.getLogger("voicedose.server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database initialization and seeding."""
    logger.info("Initializing VoiceDose SQLite database...")
    init_db()
    seed_fake_data(force=False)
    if not GNANI_API_KEY:
        logger.warning(
            "WARNING: GNANI_API_KEY is not configured! Please check your .env file."
        )
    else:
        logger.info("Gnani API key loaded successfully.")
    yield
    logger.info("VoiceDose shutting down.")

# Initialize database on import as well (essential for serverless runtimes like Vercel)
try:
    init_db()
    seed_fake_data(force=False)
except Exception as e:
    logger.warning(f"Initial DB check warning: {e}")


app = FastAPI(
    title="VoiceDose - Voice Medication Reminder for Elders",
    description="A multi-lingual, voice-first medication assistant powered by Gnani Timbre TTS and Prisma STT.",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static directory for CSS, JS, and HTML assets
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --------------------------------------------------------------------------
# Frontend Page Routes
# --------------------------------------------------------------------------

@app.get("/")
async def serve_patient_home():
    """Serve the voice-first Patient Reminder interface."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/caregiver")
async def serve_caregiver_dashboard():
    """Serve the Caregiver Monitoring Dashboard."""
    return FileResponse(str(STATIC_DIR / "caregiver.html"))


# --------------------------------------------------------------------------
# Patient & Dose API Endpoints
# --------------------------------------------------------------------------

@app.get("/api/patient")
async def api_get_patient(patient_id: int = 1):
    """Retrieve patient profile, caregiver info, and today's doses."""
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    doses = get_today_doses(patient_id)
    active_dose = get_active_dose(patient_id)
    return {
        "patient": patient,
        "doses": doses,
        "active_dose": active_dose,
        "supported_languages": SUPPORTED_LANGUAGES,
    }


@app.get("/api/active-dose")
async def api_get_active_dose(patient_id: int = 1):
    """Get the dose currently due or awaiting response."""
    dose = get_active_dose(patient_id)
    if not dose:
        raise HTTPException(status_code=404, detail="No active dose found")
    return dose


class ReminderSpeechRequest(BaseModel):
    dose_id: int
    language_code: Optional[str] = DEFAULT_LANGUAGE


@app.post("/api/reminder-speech")
async def api_get_reminder_speech(req: ReminderSpeechRequest):
    """
    Step 1: Generate spoken reminder using Gnani Timbre TTS.
    Builds localized reminder text and returns binary WAV audio stream.
    """
    dose = get_dose_by_id(req.dose_id)
    if not dose:
        raise HTTPException(status_code=404, detail="Dose not found")

    patient = get_patient(dose["patient_id"])
    patient_name = patient["name"] if patient else "Anasuya Devi"

    reminder_text = generate_reminder_text(
        patient_name=patient_name,
        slot_name=dose["slot_name"],
        medicine_name=dose["medicine_name"],
        dosage=dose["dosage"],
        instructions=dose["instructions"],
        language_code=req.language_code or DEFAULT_LANGUAGE,
    )

    # Call Gnani Timbre TTS
    audio_bytes = await synthesize_speech(
        text=reminder_text,
        language_code=req.language_code or DEFAULT_LANGUAGE,
    )

    if not audio_bytes:
        raise HTTPException(
            status_code=502,
            detail="Failed to synthesize speech via Gnani Timbre TTS. Please check server logs.",
        )

    # Return audio with metadata headers
    headers = {
        "Content-Type": "audio/wav",
        "X-Reminder-Text": quote(reminder_text.encode("utf-8")),
    }
    return Response(content=audio_bytes, media_type="audio/wav", headers=headers)


# --------------------------------------------------------------------------
# Voice Processing Pipeline (Steps 2, 3, 4)
# --------------------------------------------------------------------------

@app.post("/api/process-voice")
async def api_process_voice(
    audio: UploadFile = File(...),
    dose_id: int = Form(...),
    language_code: str = Form(DEFAULT_LANGUAGE),
):
    """
    Core Voice Flow:
    1. Receive recorded audio blob from browser.
    2. Transcribe via Gnani Prisma STT (te-IN / hi-IN / en-IN).
    3. Match transcript against Telugu, Hindi, Hinglish, and English intent keywords.
    4. Update SQLite dose record ('taken', 'pending', 'snoozed').
    5. Speak confirmation response using Gnani Timbre TTS.
    6. Return result and audio payload for immediate client playback.
    """
    dose = get_dose_by_id(dose_id)
    if not dose:
        raise HTTPException(status_code=404, detail=f"Dose id {dose_id} not found")

    # Read uploaded audio bytes
    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Empty or invalid audio recorded.")

    content_type = audio.content_type or "audio/webm"
    filename = audio.filename or "recording.webm"

    logger.info(
        f"Processing voice upload: dose_id={dose_id}, size={len(audio_bytes)}B, mime={content_type}, lang={language_code}"
    )

    # Step A: Gnani Prisma STT Transcription
    stt_result = await transcribe_audio(
        audio_bytes=audio_bytes,
        filename=filename,
        content_type=content_type,
        language_code=language_code,
    )

    transcript = stt_result.get("transcript", "").strip()
    if not transcript:
        # Fallback if silence or unrecognized
        transcript = "[No clear speech detected]"
        logger.warning("Prisma STT returned an empty transcript.")

    # Step B: Keyword and Intent Matching
    intent_data = match_intent(transcript, language_code=language_code)
    intent = intent_data["intent"]  # 'taken', 'not_yet', 'snooze', 'unknown'

    # Step C: Update SQLite Dose Status
    if intent == "taken":
        new_status = "taken"
    elif intent == "snooze":
        new_status = "snoozed"
    elif intent == "not_yet":
        new_status = "pending"
    else:
        new_status = dose["status"]  # Keep existing status if unknown

    updated_dose = update_dose_status(
        dose_id=dose_id,
        status=new_status,
        transcript=transcript,
        matched_intent=intent,
        snooze_minutes=10,
    )

    # Step D: Generate Confirmation Message & Speak via Timbre TTS
    confirmation_text = get_confirmation_text(intent, language_code=language_code)
    confirmation_audio = await synthesize_speech(
        text=confirmation_text,
        language_code=language_code,
    )

    audio_base64 = None
    if confirmation_audio:
        audio_base64 = base64.b64encode(confirmation_audio).decode("utf-8")

    # Step E: Log interaction
    log_voice_interaction(
        dose_id=dose_id,
        language_code=language_code,
        transcript=transcript,
        matched_intent=intent,
        confirmation_spoken=confirmation_text,
        success=stt_result.get("success", False),
    )

    return {
        "success": True,
        "transcript": transcript,
        "intent": intent,
        "matched_keyword": intent_data.get("matched_keyword"),
        "explanation": intent_data.get("explanation"),
        "confirmation_text": confirmation_text,
        "audio_base64": audio_base64,
        "dose": updated_dose,
        "stt_model": stt_result.get("model", "prisma-v3.0"),
    }


class SimulationRequest(BaseModel):
    dose_id: int
    text: str
    language_code: Optional[str] = DEFAULT_LANGUAGE


@app.post("/api/simulate-voice")
async def api_simulate_voice(req: SimulationRequest):
    """
    Test helper for 60-second video demo or environments without a physical mic.
    Simulates speech input, matches intent, logs to SQLite, and speaks Timbre confirmation.
    """
    dose = get_dose_by_id(req.dose_id)
    if not dose:
        raise HTTPException(status_code=404, detail="Dose not found")

    intent_data = match_intent(req.text, language_code=req.language_code or DEFAULT_LANGUAGE)
    intent = intent_data["intent"]

    if intent == "taken":
        new_status = "taken"
    elif intent == "snooze":
        new_status = "snoozed"
    elif intent == "not_yet":
        new_status = "pending"
    else:
        new_status = dose["status"]

    updated_dose = update_dose_status(
        dose_id=req.dose_id,
        status=new_status,
        transcript=req.text,
        matched_intent=intent,
        snooze_minutes=10,
    )

    confirmation_text = get_confirmation_text(intent, language_code=req.language_code or DEFAULT_LANGUAGE)
    confirmation_audio = await synthesize_speech(
        text=confirmation_text,
        language_code=req.language_code or DEFAULT_LANGUAGE,
    )

    audio_base64 = None
    if confirmation_audio:
        audio_base64 = base64.b64encode(confirmation_audio).decode("utf-8")

    log_voice_interaction(
        dose_id=req.dose_id,
        language_code=req.language_code or DEFAULT_LANGUAGE,
        transcript=req.text,
        matched_intent=intent,
        confirmation_spoken=confirmation_text,
        success=True,
    )

    return {
        "success": True,
        "transcript": req.text,
        "intent": intent,
        "matched_keyword": intent_data.get("matched_keyword"),
        "explanation": intent_data.get("explanation"),
        "confirmation_text": confirmation_text,
        "audio_base64": audio_base64,
        "dose": updated_dose,
    }


# --------------------------------------------------------------------------
# Caregiver Monitoring Endpoints (Step 5)
# --------------------------------------------------------------------------

@app.get("/api/caregiver/summary")
async def api_caregiver_summary(patient_id: int = 1):
    """
    Retrieve today's dose summary, adherence statistics, and recent voice activity logs.
    """
    patient = get_patient(patient_id)
    doses = get_today_doses(patient_id)
    stats = get_caregiver_stats(patient_id)
    logs = get_recent_logs(limit=15)

    return {
        "patient": patient,
        "doses": doses,
        "stats": stats,
        "recent_logs": logs,
    }


class CaregiverDoseUpdate(BaseModel):
    dose_id: int
    status: str  # 'taken', 'missed', 'snoozed', 'pending'
    notes: Optional[str] = None


@app.post("/api/caregiver/update-dose")
async def api_caregiver_update_dose(req: CaregiverDoseUpdate):
    """Allow caregiver to manually update dose status or add notes."""
    if req.status not in ["taken", "missed", "snoozed", "pending"]:
        raise HTTPException(status_code=400, detail="Invalid status provided.")

    updated_dose = update_dose_status(
        dose_id=req.dose_id,
        status=req.status,
        transcript=f"Caregiver manual override: {req.status.upper()}",
        matched_intent="caregiver_action",
    )
    return {"success": True, "dose": updated_dose}


@app.post("/api/reset-demo")
async def api_reset_demo():
    """Reset database to initial pristine state for clean demo presentation."""
    return reset_demo_data()
