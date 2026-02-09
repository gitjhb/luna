"""
Vercel Serverless Entry Point
"""
from app.main import app

# Vercel expects 'app' or 'handler' at module level
# FastAPI app is already ASGI-compatible
