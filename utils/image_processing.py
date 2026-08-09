"""
ROI handling.

The original implementation called cv2.selectROI(), which opens a
native desktop window — that only works on a machine with a display
attached to the Flask process, and blocks the request thread while
waiting for someone to interact with a window nobody can see on a
server. It has no place in a web app.

ROI selection now happens client-side (the operator drags a box over
the image in the browser); this module just validates and crops the
rectangle the browser reports.
"""

from __future__ import annotations

import os
import uuid

import cv2


class ROIError(ValueError):
    pass


def clamp_roi(roi: tuple, image_width: int, image_height: int) -> tuple:
    """Clip a (x, y, w, h) box to the image bounds and validate it."""
    x, y, w, h = roi
    x = max(0, min(int(x), image_width - 1))
    y = max(0, min(int(y), image_height - 1))
    w = max(1, min(int(w), image_width - x))
    h = max(1, min(int(h), image_height - y))
    return x, y, w, h


def crop_roi(image_path: str, roi: tuple, roi_folder: str) -> str:
    """
    Crop `roi` = (x, y, w, h) out of the image at image_path and save
    it to roi_folder under a random filename. Returns the saved path.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ROIError(f"Could not read image at '{image_path}'.")

    height, width = image.shape[:2]
    x, y, w, h = clamp_roi(roi, width, height)

    cropped = image[y : y + h, x : x + w]
    if cropped.size == 0:
        raise ROIError("Selected region is empty after clamping to image bounds.")

    os.makedirs(roi_folder, exist_ok=True)
    roi_path = os.path.join(roi_folder, f"roi_{uuid.uuid4().hex}.png")
    cv2.imwrite(roi_path, cropped)
    return roi_path


def scale_roi(roi: tuple, from_size: tuple, to_size: tuple) -> tuple:
    """
    Scale an ROI selected on an image of `from_size` (w, h) so it lines
    up on an image of `to_size` (w, h) — used when the reference and a
    live camera frame have different resolutions.
    """
    from_w, from_h = from_size
    to_w, to_h = to_size
    if from_w <= 0 or from_h <= 0:
        raise ROIError("Invalid source dimensions for ROI scaling.")

    scale_x = to_w / from_w
    scale_y = to_h / from_h
    x, y, w, h = roi
    return (
        int(x * scale_x),
        int(y * scale_y),
        int(w * scale_x),
        int(h * scale_y),
    )


def image_dimensions(image_path: str) -> tuple:
    image = cv2.imread(image_path)
    if image is None:
        raise ROIError(f"Could not read image at '{image_path}'.")
    h, w = image.shape[:2]
    return w, h
