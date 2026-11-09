"""
VoiceDose - Gnani AI Client Module (Timbre TTS & Prisma STT)
============================================================
This module encapsulates all communications with Gnani.ai's Inya VoiceOS:
1. Timbre TTS (Text-to-Speech):
   - Endpoint: POST https://api.vachana.ai/api/v1/tts/inference
   - Header: X-API-Key-ID
   - Synthesizes warm, natural spoken reminders in Telugu, Hindi, and English.
2. Prisma STT (Speech-to-Text):
   - Endpoint: POST https://api.vachana.ai/stt/v3
   - Header: X-API-Key-ID
   - Transcribes elderly voice responses captured in the browser.

Error Handling:
As specified in requirements, every API call validates responses and prints
detailed error messages with status code and body if an issue occurs.
"""

import sys
import logging
import httpx
from typing import Optional, Dict, Any
from app.config import (
    GNANI_API_KEY,
    GNANI_TTS_URL,
    GNANI_STT_URL,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
)

# Setup logger for Gnani client
logger = logging.getLogger("voicedose.gnani")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def synthesize_speech(
    text: str,
    language_code: str = DEFAULT_LANGUAGE,
    voice: Optional[str] = None,
    model: Optional[str] = None,
    speed: Optional[float] = None,
) -> Optional[bytes]:
    """
    Call Gnani Timbre TTS REST API to convert text to speech audio.

    Args:
        text: The text to be spoken aloud (in Telugu, Hindi, or English).
        language_code: 'te-IN', 'hi-IN', or 'en-IN'.
        voice: Optional voice name (defaults to configured voice, e.g. 'Shivani').
        model: Optional model name (defaults to 'timbre-v3.0').
        speed: Speech rate (defaults to 0.95 for clear elderly comprehension).

    Returns:
        Binary WAV audio bytes on success, or None on failure.
    """
    if not GNANI_API_KEY:
        error_msg = "[Gnani TTS Error] GNANI_API_KEY is not set in environment or .env file."
        print(error_msg, file=sys.stderr)
        logger.error(error_msg)
        return None

    lang_cfg = SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    selected_voice = voice or lang_cfg.get("voice", "Shivani")
    selected_model = model or lang_cfg.get("model", "timbre-v3.0")
    selected_speed = speed if speed is not None else lang_cfg.get("speed", 0.95)

    payload = {
        "text": text,
        "voice": selected_voice,
        "model": selected_model,
        "language": language_code,
        "speed": selected_speed,
        "audio_config": {
            "encoding": "linear_pcm",
            "container": "wav",
            "num_channels": 1,
            "sample_rate": 24000,
            "sample_width": 2,
        },
    }

    headers = {
        "X-API-Key-ID": GNANI_API_KEY,
        "Content-Type": "application/json",
    }

    logger.info(
        f"Requesting Timbre TTS ({language_code}, voice={selected_voice}, model={selected_model}): {text[:50]}..."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GNANI_TTS_URL, json=payload, headers=headers)

            if response.status_code == 200:
                audio_bytes = response.content
                logger.info(f"Timbre TTS Success: Received {len(audio_bytes)} audio bytes.")
                return audio_bytes
            else:
                error_msg = (
                    f"[Gnani TTS Error] HTTP {response.status_code} calling {GNANI_TTS_URL}:\n"
                    f"Response Body: {response.text}"
                )
                print(error_msg, file=sys.stderr)
                logger.error(error_msg)
                return None

    except httpx.RequestError as exc:
        error_msg = f"[Gnani TTS Connection Error] Network error requesting {exc.request.url!r}: {exc}"
        print(error_msg, file=sys.stderr)
        logger.error(error_msg)
        return None
    except Exception as exc:
        error_msg = f"[Gnani TTS Unexpected Error] An unexpected error occurred: {exc}"
        print(error_msg, file=sys.stderr)
        logger.error(error_msg)
        return None


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "user_response.webm",
    content_type: str = "audio/webm",
    language_code: str = DEFAULT_LANGUAGE,
) -> Dict[str, Any]:
    """
    Call Gnani Prisma STT v3 REST API to transcribe recorded user speech.

    Args:
        audio_bytes: The raw audio bytes recorded in the browser (WAV or WebM).
        filename: Filename with extension (e.g. 'audio.webm' or 'audio.wav').
        content_type: MIME type of audio (e.g. 'audio/webm', 'audio/wav').
        language_code: 'te-IN', 'hi-IN', or 'en-IN'.

    Returns:
        Dict with keys:
            success (bool): True if transcription succeeded.
            transcript (str): The recognized text transcript.
            model (str): Model name (e.g. 'prisma-v2.5' or 'prisma-v3.0').
            error (str | None): Error message if failed.
    """
    if not GNANI_API_KEY:
        error_msg = "[Gnani STT Error] GNANI_API_KEY is not set in environment or .env file."
        print(error_msg, file=sys.stderr)
        logger.error(error_msg)
        return {
            "success": False,
            "transcript": "",
            "error": error_msg,
        }

    headers = {
        "X-API-Key-ID": GNANI_API_KEY,
    }

    files = {
        "audio_file": (filename, audio_bytes, content_type),
    }

    data = {
        "language_code": language_code,
    }

    logger.info(
        f"Requesting Prisma STT ({language_code}, size={len(audio_bytes)} bytes, mime={content_type})..."
    )

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                GNANI_STT_URL,
                headers=headers,
                files=files,
                data=data,
            )

            if response.status_code == 200:
                result = response.json()
                transcript = result.get("transcript", "").strip()
                logger.info(f"Prisma STT Success: Transcript='{transcript}'")
                return {
                    "success": True,
                    "transcript": transcript,
                    "detected_language": result.get("detected_language_code", language_code),
                    "model": result.get("model", "prisma-v3.0"),
                    "raw_response": result,
                    "error": None,
                }
            else:
                error_msg = (
                    f"[Gnani STT Error] HTTP {response.status_code} calling {GNANI_STT_URL}:\n"
                    f"Response Body: {response.text}"
                )
                print(error_msg, file=sys.stderr)
                logger.error(error_msg)
                return {
                    "success": False,
                    "transcript": "",
                    "error": error_msg,
                }

    except httpx.RequestError as exc:
        error_msg = f"[Gnani STT Connection Error] Network error requesting {exc.request.url!r}: {exc}"
        print(error_msg, file=sys.stderr)
        logger.error(error_msg)
        return {
            "success": False,
            "transcript": "",
            "error": error_msg,
        }
    except Exception as exc:
        error_msg = f"[Gnani STT Unexpected Error] An unexpected error occurred: {exc}"
        print(error_msg, file=sys.stderr)
        logger.error(error_msg)
        return {
            "success": False,
            "transcript": "",
            "error": error_msg,
        }
