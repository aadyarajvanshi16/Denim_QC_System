"""
Validation helpers for anything that comes from outside the process:
uploaded files and the RTSP URL an operator types in.
"""

import os
import re
import uuid
from urllib.parse import urlparse

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}


class UploadError(ValueError):
    """Raised for any invalid/unsafe upload. Caller turns this into a 400."""


def _extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def validate_and_save_image(file_storage, dest_folder: str, max_bytes: int) -> str:
    """
    Validate an uploaded image (extension, size, that it's actually a
    decodable image) and save it under a random, collision-free name.
    Returns the absolute path written.

    Never trusts the client-supplied filename for anything other than
    reading its extension.
    """
    if file_storage is None or file_storage.filename == "":
        raise UploadError("No file was uploaded.")

    original_name = secure_filename(file_storage.filename)
    ext = _extension(original_name)
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise UploadError(
            f"Unsupported file type '.{ext}'. Allowed: "
            + ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        )

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise UploadError("Uploaded file is empty.")
    if size > max_bytes:
        raise UploadError(f"File too large (max {max_bytes // (1024 * 1024)}MB).")

    # Confirm it's actually a decodable image, not just a renamed file.
    try:
        img = Image.open(file_storage.stream)
        img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadError("File is not a valid or is a corrupted image.") from exc
    finally:
        file_storage.stream.seek(0)

    os.makedirs(dest_folder, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    dest_path = os.path.join(dest_folder, safe_name)
    file_storage.save(dest_path)
    return dest_path, original_name


_RTSP_RE = re.compile(r"^rtsp://[a-zA-Z0-9\.\-_:@/]+$")


def validate_rtsp_url(url: str) -> str:
    """
    Restrict RTSP URLs to a safe character set and scheme before they
    ever reach OpenCV, so a malicious value can't smuggle shell/path
    tricks through cv2.VideoCapture.
    """
    url = (url or "").strip()
    if not url:
        raise UploadError("RTSP URL is required.")
    if len(url) > 500:
        raise UploadError("RTSP URL is too long.")
    if not _RTSP_RE.match(url):
        raise UploadError("RTSP URL contains invalid characters or is not an rtsp:// URL.")

    parsed = urlparse(url)
    if parsed.scheme != "rtsp" or not parsed.hostname:
        raise UploadError("Invalid RTSP URL.")
    return url


_SAFE_REPORT_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,120}$")


def safe_report_basename(name: str) -> str:
    """
    Used for rename_report's *new* name (user-chosen) — restrict to a
    small safe character set so it can never escape the reports folder.
    """
    name = (name or "").strip()
    if not _SAFE_REPORT_NAME_RE.match(name):
        raise UploadError(
            "Report name may only contain letters, numbers, hyphens and underscores."
        )
    return name


def safe_existing_report_path(saved_reports_folder: str, filename: str) -> str:
    """
    Resolve a filename that must already exist inside saved_reports_folder,
    rejecting any path-traversal attempt (../, absolute paths, symlinked
    escapes) by checking the resolved path is still inside the folder.
    """
    base = os.path.realpath(saved_reports_folder)
    candidate = os.path.realpath(os.path.join(base, secure_filename(filename)))
    if not candidate.startswith(base + os.sep):
        raise UploadError("Invalid report filename.")
    if not os.path.isfile(candidate):
        raise UploadError("Report not found.")
    return candidate
