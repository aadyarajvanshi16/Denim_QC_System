import logging
import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from decorators import permission_required
from models import Inspection, RecipeExtraction
from utils.pdf_reports import build_inspection_report, build_recipe_report
from utils.validators import UploadError, safe_existing_report_path, safe_report_basename

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/ai_reports")
@login_required
@permission_required("ai_reports")
def ai_reports():
    folder = current_app.config["SAVED_REPORTS_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    reports = sorted(os.listdir(folder), reverse=True)
    return render_template("ai_reports.html", reports=reports)


@reports_bp.route("/download_saved_report/<path:filename>")
@login_required
@permission_required("ai_reports")
def download_saved_report(filename):
    try:
        path = safe_existing_report_path(current_app.config["SAVED_REPORTS_FOLDER"], filename)
    except UploadError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("reports.ai_reports"))
    return send_file(path, as_attachment=True)


@reports_bp.route("/delete_report/<path:filename>", methods=["POST"])
@login_required
@permission_required("ai_reports")
def delete_report(filename):
    try:
        path = safe_existing_report_path(current_app.config["SAVED_REPORTS_FOLDER"], filename)
        os.remove(path)
        flash("Report deleted.", "success")
    except UploadError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("reports.ai_reports"))


@reports_bp.route("/rename_report", methods=["POST"])
@login_required
@permission_required("ai_reports")
def rename_report():
    folder = current_app.config["SAVED_REPORTS_FOLDER"]
    try:
        old_path = safe_existing_report_path(folder, request.form.get("old_name", ""))
        new_basename = safe_report_basename(request.form.get("new_name", ""))
    except UploadError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("reports.ai_reports"))

    new_path = os.path.join(os.path.realpath(folder), new_basename + ".pdf")
    if os.path.exists(new_path):
        flash("A report with that name already exists.", "danger")
        return redirect(url_for("reports.ai_reports"))

    os.rename(old_path, new_path)
    flash("Report renamed.", "success")
    return redirect(url_for("reports.ai_reports"))


@reports_bp.route("/download_report/<int:inspection_id>")
@login_required
@permission_required("ai_reports")
def download_report(inspection_id):
    inspection = Inspection.query.get_or_404(inspection_id)

    folder = current_app.config["SAVED_REPORTS_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    filename = f"Denim_Report_{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}.pdf"
    pdf_path = os.path.join(folder, filename)

    build_inspection_report(inspection, pdf_path)
    return send_file(pdf_path, as_attachment=True)


@reports_bp.route("/download_recipe_report/<int:recipe_id>")
@login_required
@permission_required("ai_reports")
def download_recipe_report(recipe_id):
    record = RecipeExtraction.query.get_or_404(recipe_id)

    folder = current_app.config["SAVED_REPORTS_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    filename = f"Recipe_Report_{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}.pdf"
    pdf_path = os.path.join(folder, filename)

    build_recipe_report(record, pdf_path)
    return send_file(pdf_path, as_attachment=True)
