import json
import logging
import os
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from decorators import permission_required
from extensions import db
from models import AppSetting, Inspection, RecipeExtraction
from utils.charts import generate_charts
from utils.color_analysis import ImageReadError, analyze_images
from utils.image_processing import ROIError, crop_roi, image_dimensions
from utils.recipe_engine import extract_recipe_from_image, generate_recipe
from utils.validators import UploadError, validate_and_save_image

logger = logging.getLogger(__name__)
inspection_bp = Blueprint("inspection", __name__)


def _confidence_from_delta_e(delta_e: float) -> float:
    return max(0.0, round(100 - delta_e * 5, 2))


def _qc_status(delta_e: float) -> str:
    pass_t = AppSetting.get_float("delta_e_pass_threshold", current_app.config["DELTA_E_PASS_THRESHOLD"])
    acceptable_t = AppSetting.get_float(
        "delta_e_acceptable_threshold", current_app.config["DELTA_E_ACCEPTABLE_THRESHOLD"]
    )
    if delta_e < pass_t:
        return "APPROVED"
    if delta_e < acceptable_t:
        return "ACCEPTABLE"
    return "REJECTED"


# ======================================================================
# FABRIC COMPARISON
# ======================================================================


@inspection_bp.route("/fabric_comparison")
@login_required
@permission_required("fabric_comparison")
def fabric_comparison():
    return render_template("fabric_comparison.html")


@inspection_bp.route("/fabric_comparison/upload", methods=["POST"])
@login_required
@permission_required("fabric_comparison")
def fabric_comparison_upload():
    try:
        ref_path, ref_name = validate_and_save_image(
            request.files.get("reference"),
            current_app.config["UPLOAD_FOLDER"],
            current_app.config["MAX_CONTENT_LENGTH"],
        )
        test_path, test_name = validate_and_save_image(
            request.files.get("test"),
            current_app.config["UPLOAD_FOLDER"],
            current_app.config["MAX_CONTENT_LENGTH"],
        )
    except UploadError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("inspection.fabric_comparison"))

    ref_w, ref_h = image_dimensions(ref_path)
    test_w, test_h = image_dimensions(test_path)

    session["compare"] = {
        "ref_path": ref_path,
        "ref_name": ref_name,
        "test_path": test_path,
        "test_name": test_name,
    }

    return render_template(
        "roi_select_pair.html",
        ref_url="/" + ref_path,
        test_url="/" + test_path,
        ref_dims=(ref_w, ref_h),
        test_dims=(test_w, test_h),
        analyze_url=url_for("inspection.fabric_comparison_analyze"),
    )


@inspection_bp.route("/fabric_comparison/analyze", methods=["POST"])
@login_required
@permission_required("fabric_comparison")
def fabric_comparison_analyze():
    staged = session.get("compare")
    if not staged:
        flash("Your upload session expired — please upload the images again.", "warning")
        return redirect(url_for("inspection.fabric_comparison"))

    try:
        ref_roi_coords = _parse_roi(request.form, "ref")
        test_roi_coords = _parse_roi(request.form, "test")

        ref_roi = crop_roi(staged["ref_path"], ref_roi_coords, current_app.config["ROI_FOLDER"])
        test_roi = crop_roi(staged["test_path"], test_roi_coords, current_app.config["ROI_FOLDER"])

        analysis = analyze_images(ref_roi, test_roi)
    except (ROIError, ImageReadError, ValueError, KeyError) as exc:
        logger.warning("Fabric comparison failed: %s", exc)
        flash(f"Could not analyze the selected regions: {exc}", "danger")
        return redirect(url_for("inspection.fabric_comparison"))

    confidence = _confidence_from_delta_e(analysis["delta_e"])
    recipe = generate_recipe(analysis["lab1"], analysis["lab2"])

    result_folder = current_app.config["RESULT_FOLDER"]
    bar_chart, pie_chart = generate_charts(analysis["lab1"], analysis["lab2"], result_folder)

    ref_static = os.path.join(result_folder, "ref_roi_" + os.path.basename(ref_roi))
    test_static = os.path.join(result_folder, "test_roi_" + os.path.basename(test_roi))
    os.replace(ref_roi, ref_static) if os.path.exists(ref_roi) else None
    os.replace(test_roi, test_static) if os.path.exists(test_roi) else None

    qc_status = _qc_status(analysis["delta_e"])
    comp_id = "COMP-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    inspection = Inspection(
        comp_id=comp_id,
        operator_id=current_user.id,
        reference_filename=staged["ref_name"],
        test_filename=staged["test_name"],
        ref_roi_path=ref_static,
        test_roi_path=test_static,
        lab1_l=analysis["lab1"][0],
        lab1_a=analysis["lab1"][1],
        lab1_b=analysis["lab1"][2],
        lab2_l=analysis["lab2"][0],
        lab2_a=analysis["lab2"][1],
        lab2_b=analysis["lab2"][2],
        delta_e=analysis["delta_e"],
        similarity=analysis["similarity"],
        confidence=confidence,
        status="PASS" if analysis["status"] == "PASS" else "FAIL",
        bar_chart=bar_chart,
        pie_chart=pie_chart,
        dominant1_json=json.dumps(analysis["dominant1"]),
        dominant2_json=json.dumps(analysis["dominant2"]),
        recipe_json=json.dumps(recipe),
    )
    db.session.add(inspection)
    db.session.commit()
    session.pop("compare", None)

    return render_template(
        "result.html",
        delta_e=analysis["delta_e"],
        similarity=analysis["similarity"],
        status=analysis["status"],
        qc_status=qc_status,
        lab1=analysis["lab1"],
        lab2=analysis["lab2"],
        dominant1=analysis["dominant1"],
        dominant2=analysis["dominant2"],
        ref_roi="/" + ref_static,
        test_roi="/" + test_static,
        bar_chart=bar_chart,
        pie_chart=pie_chart,
        confidence=confidence,
        recipe=recipe,
        comp_id=comp_id,
        inspection_id=inspection.id,
    )


def _parse_roi(form, prefix: str) -> tuple:
    try:
        x = float(form[f"{prefix}_x"])
        y = float(form[f"{prefix}_y"])
        w = float(form[f"{prefix}_w"])
        h = float(form[f"{prefix}_h"])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Missing or invalid ROI for '{prefix}'.") from exc
    if w <= 0 or h <= 0:
        raise ValueError(f"Selected region for '{prefix}' has zero area — draw a box on the image.")
    return x, y, w, h


# ======================================================================
# RECIPE EXTRACTION
# ======================================================================


@inspection_bp.route("/recipe_extraction")
@login_required
@permission_required("recipe_extraction")
def recipe_extraction():
    return render_template("recipe_extraction.html")


@inspection_bp.route("/recipe_extraction/upload", methods=["POST"])
@login_required
@permission_required("recipe_extraction")
def recipe_extraction_upload():
    try:
        image_path, image_name = validate_and_save_image(
            request.files.get("image"),
            current_app.config["UPLOAD_FOLDER"],
            current_app.config["MAX_CONTENT_LENGTH"],
        )
    except UploadError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("inspection.recipe_extraction"))

    w, h = image_dimensions(image_path)
    session["recipe_source"] = {"path": image_path, "name": image_name}

    return render_template(
        "roi_select_single.html",
        image_url="/" + image_path,
        dims=(w, h),
        analyze_url=url_for("inspection.recipe_extraction_analyze"),
    )


@inspection_bp.route("/recipe_extraction/analyze", methods=["POST"])
@login_required
@permission_required("recipe_extraction")
def recipe_extraction_analyze():
    staged = session.get("recipe_source")
    if not staged:
        flash("Your upload session expired — please upload the sample again.", "warning")
        return redirect(url_for("inspection.recipe_extraction"))

    try:
        roi_coords = _parse_roi(request.form, "roi")
        roi_path = crop_roi(staged["path"], roi_coords, current_app.config["ROI_FOLDER"])
        analysis = analyze_images(roi_path, roi_path)
    except (ROIError, ImageReadError, ValueError, KeyError) as exc:
        logger.warning("Recipe extraction failed: %s", exc)
        flash(f"Could not analyze the selected region: {exc}", "danger")
        return redirect(url_for("inspection.recipe_extraction"))

    recipe = extract_recipe_from_image(analysis["lab1"], analysis["dominant1"])

    final_roi_path = os.path.join(current_app.config["RESULT_FOLDER"], "recipe_" + os.path.basename(roi_path))
    os.replace(roi_path, final_roi_path)

    record = RecipeExtraction(
        operator_id=current_user.id,
        source_filename=staged["name"],
        roi_path=final_roi_path,
        lab_l=analysis["lab1"][0],
        lab_a=analysis["lab1"][1],
        lab_b=analysis["lab1"][2],
        dominant_json=json.dumps(analysis["dominant1"]),
        recipe_json=json.dumps(recipe),
    )
    db.session.add(record)
    db.session.commit()
    session.pop("recipe_source", None)
    session["last_recipe_extraction_id"] = record.id

    return render_template(
        "single_recipe.html",
        recipe=recipe,
        roi="/" + final_roi_path,
        lab=analysis["lab1"],
        dominant=analysis["dominant1"],
        recipe_id=record.id,
    )


# ======================================================================
# LIVE QUALITY (page only — camera/RTSP endpoints live in blueprints/api.py)
# ======================================================================


@inspection_bp.route("/live_quality")
@login_required
@permission_required("live_quality")
def live_quality():
    return render_template("live_quality.html")
