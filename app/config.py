"""
VoiceDose - Configuration Module
=================================
This file handles application settings and environment variables.
It securely loads the Gnani AI API key from the .env file and configures
the default endpoints, voices, and language codes for Timbre TTS and Prisma STT.

Key Responsibilities:
- Load GNANI_API_KEY from .env without hardcoding secrets.
- Define endpoints for Gnani Timbre TTS and Prisma STT REST APIs.
- Configure supported language codes (Telugu, Hindi, English).
- Provide application defaults and database paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env in project root
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# Gnani / Vachana API credentials & endpoints
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_TTS_URL = os.getenv("GNANI_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference")
GNANI_STT_URL = os.getenv("GNANI_STT_URL", "https://api.vachana.ai/stt/v3")

# Detect Vercel serverless environment
IS_VERCEL = bool(os.getenv("VERCEL"))

# SQLite Database path
if IS_VERCEL:
    DATABASE_PATH = Path("/tmp/voicedose.db")
else:
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DATABASE_PATH = DATA_DIR / "voicedose.db"

# Language and Voice mapping
# Timbre v3.0 supports 10 Indian languages natively with voices like 'Shivani'
SUPPORTED_LANGUAGES = {
    "te-IN": {
        "code": "te-IN",
        "name": "Telugu",
        "native_name": "తెలుగు",
        "voice": "Shivani",
        "model": "timbre-v3.0",
        "speed": 0.95,  # Gentle, calm pace for elderly comprehension
    },
    "hi-IN": {
        "code": "hi-IN",
        "name": "Hindi",
        "native_name": "हिंदी",
        "voice": "Shivani",
        "model": "timbre-v3.0",
        "speed": 0.95,
    },
    "en-IN": {
        "code": "en-IN",
        "name": "English",
        "native_name": "English",
        "voice": "Shivani",
        "model": "timbre-v3.0",
        "speed": 0.95,
    },
}

DEFAULT_LANGUAGE = "te-IN"
