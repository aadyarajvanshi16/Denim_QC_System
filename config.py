"""
Application configuration.

Nothing sensitive is hardcoded here. Everything is read from the
environment (or a local .env file when python-dotenv is installed),
so this file is safe to commit.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()  # no-op in prod if there's no .env file

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _abs_path(*parts: str) -> str:
    """Resolve a path relative to this file's directory, never the
    process's current working directory — the CWD differs depending on
    whether you run `flask --app app ...`, `python wsgi.py`, or launch
    from an IDE, which is what causes 'unable to open database file'
    on Windows when a plain relative path is used."""
    return os.path.join(BASE_DIR, *parts)


class Config:
    # ------------------------------------------------------------------
    # Core Flask
    # ------------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is not set. Create a .env file (see .env.example) "
            "or export SECRET_KEY before starting the app."
        )

    DEBUG = _env_bool("FLASK_DEBUG", default=False)
    TESTING = False

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    # Absolute by default (see _abs_path) so it works the same no matter
    # what directory the process was launched from. Set DATABASE_URL in
    # .env to override with a real server (Postgres, etc).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + _abs_path("instance", "denim_qc.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # ------------------------------------------------------------------
    # Sessions / cookies
    # ------------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # ------------------------------------------------------------------
    # Uploads
    # ------------------------------------------------------------------
    # All absolute (based on this file's location), same reasoning as
    # the database path above — avoids Windows path issues when the
    # process is launched from a different working directory.
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", _abs_path("uploads"))
    ROI_FOLDER = os.path.join(UPLOAD_FOLDER, "roi")
    RESULT_FOLDER = os.environ.get("RESULT_FOLDER", _abs_path("static", "results"))
    SAVED_REPORTS_FOLDER = os.environ.get("SAVED_REPORTS_FOLDER", _abs_path("saved_reports"))

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "15")) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}

    # ------------------------------------------------------------------
    # Camera / RTSP
    # ------------------------------------------------------------------
    CAMERA_SOURCE = os.environ.get("CAMERA_SOURCE", "webcam")
    RTSP_URL = os.environ.get("RTSP_URL", "")
    RECONNECT_DELAY = int(os.environ.get("RECONNECT_DELAY", "5"))

    # ------------------------------------------------------------------
    # QC thresholds (previously hardcoded magic numbers scattered
    # through app.py — now centralised and admin-tunable via DB,
    # these are just the fallback defaults)
    # ------------------------------------------------------------------
    DELTA_E_PASS_THRESHOLD = float(os.environ.get("DELTA_E_PASS_THRESHOLD", "2.0"))
    DELTA_E_ACCEPTABLE_THRESHOLD = float(
        os.environ.get("DELTA_E_ACCEPTABLE_THRESHOLD", "5.0")
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config():
    env = os.environ.get("FLASK_ENV", "production").lower()
    return DevelopmentConfig if env == "development" else ProductionConfig
