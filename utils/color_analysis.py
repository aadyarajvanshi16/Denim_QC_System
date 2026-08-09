"""
Color analysis: average LAB extraction, dominant-color clustering,
and Delta E (CIEDE2000) comparison between a reference and test ROI.

Repeated calls with the same image (e.g. the same reference re-used
across several live-inspection frames) are cached by file content
hash, so we don't recompute KMeans/LAB conversion every request.
"""

from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache
from typing import List, TypedDict

import cv2
import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class ImageReadError(RuntimeError):
    """Raised when an image can't be read/decoded by OpenCV."""


class DominantColor(TypedDict):
    rgb: List[int]
    percentage: float


def _file_fingerprint(image_path: str) -> str:
    """Cheap content fingerprint (mtime+size) used as an LRU cache key."""
    stat = os.stat(image_path)
    return f"{image_path}:{stat.st_mtime_ns}:{stat.st_size}"


def _read_image_rgb(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path)
    if image is None:
        raise ImageReadError(f"Could not read image at '{image_path}' (missing or corrupted).")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


@lru_cache(maxsize=64)
def _extract_average_lab_cached(fingerprint: str, image_path: str):
    image = _read_image_rgb(image_path)
    image = cv2.resize(image, (300, 300))
    pixels = image.reshape((-1, 3))
    avg_rgb = np.mean(pixels, axis=0) / 255.0
    lab = rgb2lab([[avg_rgb]])[0][0]
    return tuple(float(v) for v in lab)


def extract_average_lab(image_path: str):
    return _extract_average_lab_cached(_file_fingerprint(image_path), image_path)


@lru_cache(maxsize=64)
def _extract_dominant_colors_cached(fingerprint: str, image_path: str, k: int):
    image = _read_image_rgb(image_path)
    image = cv2.resize(image, (200, 200))
    pixels = image.reshape((-1, 3))

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(pixels)
    colors = kmeans.cluster_centers_
    labels = kmeans.labels_
    counts = np.bincount(labels, minlength=k)
    percentages = counts / len(labels)

    dominant = [
        {"rgb": color.astype(int).tolist(), "percentage": round(float(pct) * 100, 2)}
        for color, pct in zip(colors, percentages)
    ]
    return tuple(
        sorted(dominant, key=lambda c: c["percentage"], reverse=True)[:k]
        for _ in [0]
    )[0]


def extract_dominant_colors(image_path: str, k: int = 3) -> List[DominantColor]:
    result = _extract_dominant_colors_cached(_file_fingerprint(image_path), image_path, k)
    # tuples -> plain dicts/lists for JSON/Jinja friendliness
    return [{"rgb": list(c["rgb"]), "percentage": c["percentage"]} for c in result]


def analyze_images(img1_path: str, img2_path: str) -> dict:
    """
    Compare two ROI images. Raises ImageReadError if either image is
    missing/corrupted — callers must catch this and return a clean
    error response rather than letting it 500.
    """
    lab1 = extract_average_lab(img1_path)
    lab2 = extract_average_lab(img2_path)
    dominant1 = extract_dominant_colors(img1_path)
    dominant2 = extract_dominant_colors(img2_path)

    delta_e = float(deltaE_ciede2000(np.array(lab1), np.array(lab2)))
    similarity = max(0.0, 100.0 - delta_e * 10)
    status = "PASS" if delta_e < 2 else "FAIL"

    return {
        "lab1": [round(x, 2) for x in lab1],
        "lab2": [round(x, 2) for x in lab2],
        "delta_e": round(delta_e, 2),
        "similarity": round(similarity, 2),
        "status": status,
        "dominant1": dominant1,
        "dominant2": dominant2,
    }
