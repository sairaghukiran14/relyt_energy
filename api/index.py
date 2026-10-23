"""Vercel entry point. Vercel runs the FastAPI app as a Python serverless function
under /api; the backend package is added to the path so `app` imports resolve.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402

# Vercel's Python runtime looks for a module-level ASGI `app`.
__all__ = ["app"]
