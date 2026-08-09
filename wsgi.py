"""
Production entrypoint.

    waitress-serve --host=0.0.0.0 --port=8000 wsgi:app

or

    python wsgi.py
"""

import os

from waitress import serve

from app import app

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    serve(app, host=host, port=port, threads=8)
