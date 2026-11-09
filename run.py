"""
VoiceDose - Server Runner Script
================================
Run this file to start the VoiceDose FastAPI server with Uvicorn:
    python run.py

Or directly with uvicorn:
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

import sys
import uvicorn
from app.config import GNANI_API_KEY

def main():
    if not GNANI_API_KEY:
        print("\n" + "=" * 60)
        print("WARNING: GNANI_API_KEY is not set in your .env file!")
        print("Please add your key to .env: GNANI_API_KEY=your_key_here")
        print("=" * 60 + "\n")
    else:
        print("\n" + "=" * 60)
        print("✓ VoiceDose: Gnani API key loaded successfully.")
        print("✓ Patient View:   http://localhost:8000/")
        print("✓ Caregiver View: http://localhost:8000/caregiver")
        print("✓ API Docs:       http://localhost:8000/docs")
        print("=" * 60 + "\n")

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
