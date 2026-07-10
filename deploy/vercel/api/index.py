import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: E402  (FastAPI ASGI app, path-independent — Vercel rewrites preserve the original request path)
