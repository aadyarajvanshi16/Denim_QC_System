"""
StreamReader: reads frames from an RTSP stream or local webcam on a
background thread, so the Flask request thread never blocks on
cv2.VideoCapture.read() (which can stall for seconds on a flaky
network camera).

Usage:
    reader = StreamReader(source, reconnect_delay=5).start()
    frame = reader.get_frame()   # None until the first frame arrives
    reader.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class StreamReader:
    def __init__(self, source, reconnect_delay: int = 5, name: str = "stream-reader"):
        """
        source: an RTSP URL string, or an int webcam index (0, 1, ...).
        """
        self.source = source
        self.reconnect_delay = max(1, reconnect_delay)
        self._name = name

        self._capture: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()

        self._running = threading.Event()
        self._connected = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> "StreamReader":
        if self._thread and self._thread.is_alive():
            return self
        self._running.set()
        self._thread = threading.Thread(target=self._run, name=self._name, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=5)
        self._release_capture()

    def get_frame(self):
        """Returns the most recent decoded frame, or None if none yet."""
        with self._frame_lock:
            return None if self._frame is None else self._frame.copy()

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def last_error(self) -> Optional[str]:
        return self._last_error

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _open_capture(self) -> bool:
        self._release_capture()
        try:
            capture = cv2.VideoCapture(self.source)
        except Exception as exc:  # pragma: no cover - defensive
            self._last_error = f"Failed to open capture: {exc}"
            logger.exception(self._last_error)
            return False

        if not capture.isOpened():
            self._last_error = f"Could not open video source: {self.source!r}"
            logger.warning(self._last_error)
            capture.release()
            return False

        self._capture = capture
        self._connected.set()
        self._last_error = None
        return True

    def _release_capture(self) -> None:
        self._connected.clear()
        if self._capture is not None:
            try:
                self._capture.release()
            except Exception:  # pragma: no cover - defensive
                pass
            self._capture = None

    def _run(self) -> None:
        while self._running.is_set():
            if self._capture is None or not self._capture.isOpened():
                if not self._open_capture():
                    time.sleep(self.reconnect_delay)
                    continue

            success, frame = self._capture.read()
            if not success or frame is None:
                self._last_error = "Camera not found / stream dropped a frame."
                logger.warning(
                    "%s: read failed, reconnecting in %ss", self._name, self.reconnect_delay
                )
                self._release_capture()
                time.sleep(self.reconnect_delay)
                continue

            with self._frame_lock:
                self._frame = frame

        self._release_capture()
