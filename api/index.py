"""
VoiceDose - Vercel Serverless Function Entrypoint
=================================================
This file exposes the FastAPI app instance for Vercel's Python runtime.
All incoming HTTP requests to Vercel are routed here via vercel.json rewrites.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path so 'app' module imports cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
