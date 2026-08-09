import logging
import os
import threading

import cv2
from flask import Blueprint, Response, current_app, jsonify, request, session
from flask_login import login_required

from decorators import permission_required
from pipeline.stream_reader import StreamReader
from utils.color_analysis import ImageReadError, analyze_images
from utils.image_processing import ROIError, crop_roi, image_dimensions, scale_roi
from utils.validators import UploadError, validate_and_save_image, validate_rtsp_url

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


class CameraManager:
    """
    A physical camera/RTSP feed is a genuinely single shared resource
    for the whole app (there's one camera on the factory floor), so
    unlike the per-user upload/ROI state this legitimately lives at
    app scope — but behind a lock, with explicit connect/disconnect,
    instead of a bare unsynchronized global variable.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._reader: StreamReader | None = None

    def connect(self, source, reconnect_delay: int) -> None:
        with self._lock:
            if self._reader is not None:
                self._reader.stop()
            self._reader = StreamReader(source, reconnect_delay=reconnect_delay).start()

    def get_frame(self):
        with self._lock:
            reader = self._reader
        return reader.get_frame() if reader else None

    def status(self) -> dict:
        with self._lock:
            reader = self._reader
        if reader is None:
            return {"status": "No Stream"}
        if not reader.is_connected():
            return {"status": "Reconnecting", "error": reader.last_error()}
        if reader.get_frame() is None:
            return {"status": "Waiting for Frames"}
        return {"status": "Receiving Frames"}

    def stop(self) -> None:
        with self._lock:
            if self._reader is not None:
                self._reader.stop()
                self._reader = None


_camera_manager = CameraManager()


@api_bp.route("/set_rtsp", methods=["POST"])
@login_required
@permission_required("live_quality")
def set_rtsp():
    try:
        rtsp_url = validate_rtsp_url(request.form.get("rtsp", ""))
    except UploadError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    _camera_manager.connect(rtsp_url, current_app.config["RECONNECT_DELAY"])
    return jsonify({"status": "connecting"})


@api_bp.route("/rtsp_status")
@login_required
@permission_required("live_quality")
def rtsp_status():
    return jsonify(_camera_manager.status())


@api_bp.route("/video_feed")
@login_required
@permission_required("live_quality")
def video_feed():
    def generate():
        while True:
            frame = _camera_manager.get_frame()
            if frame is None:
                continue
            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@api_bp.route("/upload_live_reference", methods=["POST"])
@login_required
@permission_required("live_quality")
def upload_live_reference():
    try:
        path, _name = validate_and_save_image(
            request.files.get("reference"),
            current_app.config["RESULT_FOLDER"],
            current_app.config["MAX_CONTENT_LENGTH"],
        )
    except UploadError as exc:
        return jsonify({"error": str(exc)}), 400

    w, h = image_dimensions(path)
    session["live_reference"] = {"path": path, "width": w, "height": h}
    session.pop("live_roi", None)

    return jsonify({"message": "Reference uploaded", "width": w, "height": h})


@api_bp.route("/select_live_roi", methods=["POST"])
@login_required
@permission_required("live_quality")
def select_live_roi():
    reference = session.get("live_reference")
    if not reference:
        return jsonify({"error": "Upload a reference image first."}), 400

    try:
        x = float(request.form["x"])
        y = float(request.form["y"])
        w = float(request.form["w"])
        h = float(request.form["h"])
    except (KeyError, ValueError):
        return jsonify({"error": "Invalid ROI coordinates."}), 400

    if w <= 0 or h <= 0:
        return jsonify({"error": "Draw a non-empty box on the reference image."}), 400

    session["live_roi"] = {"x": x, "y": y, "w": w, "h": h}
    return jsonify({"message": "ROI selected"})


@api_bp.route("/live_analyze", methods=["POST"])
@login_required
@permission_required("live_quality")
def live_analyze():
    reference = session.get("live_reference")
    roi = session.get("live_roi")

    if not reference:
        return jsonify({"status": "Upload a reference image first"}), 400
    if not roi:
        return jsonify({"status": "Select ROI first"}), 400
    if "frame" not in request.files:
        return jsonify({"status": "No frame received"}), 400

    frame_folder = current_app.config["RESULT_FOLDER"]
    os.makedirs(frame_folder, exist_ok=True)
    frame_path = os.path.join(frame_folder, f"live_frame_{session.get('_id', 'anon')}.jpg")
    request.files["frame"].save(frame_path)

    try:
        live_w, live_h = image_dimensions(frame_path)
        ref_roi_coords = (roi["x"], roi["y"], roi["w"], roi["h"])
        scaled_roi = scale_roi(
            ref_roi_coords, (reference["width"], reference["height"]), (live_w, live_h)
        )

        reference_roi_path = crop_roi(reference["path"], ref_roi_coords, current_app.config["ROI_FOLDER"])
        live_roi_path = crop_roi(frame_path, scaled_roi, current_app.config["ROI_FOLDER"])

        analysis = analyze_images(reference_roi_path, live_roi_path)
    except (ROIError, ImageReadError) as exc:
        logger.warning("Live analyze failed: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 400
    finally:
        for p in (locals().get("reference_roi_path"), locals().get("live_roi_path")):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    confidence = max(0.0, round(100 - analysis["delta_e"] * 5, 2))

    return jsonify(
        {
            "similarity": analysis["similarity"],
            "delta_e": analysis["delta_e"],
            "l": analysis["lab2"][0],
            "a": analysis["lab2"][1],
            "b": analysis["lab2"][2],
            "confidence": confidence,
            "status": analysis["status"],
        }
    )
