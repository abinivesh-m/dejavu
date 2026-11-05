"""Vercel serverless entry point.

Vercel runs this file as a serverless function. The FastAPI app is re-used
as-is; SQLite is seeded on cold start (ephemeral, but fine for a demo).

For a persistent memory bank, point HINDSIGHT_API_URL at Hindsight Cloud
(ui.hindsight.vectorize.io) and set HINDSIGHT_API_KEY. Use promo code
MEMHACK99 for \$50 of free credits.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dejavu.web import app  # noqa: E402

# Vercel expects the ASGI app to be named `app` (or `handler`).
handler = app
