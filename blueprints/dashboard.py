from flask import Blueprint, render_template, request
from flask_login import login_required

from decorators import admin_required
from models import Inspection

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    return render_template("index.html")


@dashboard_bp.route("/history")
@login_required
@admin_required
def history():
    q = Inspection.query.order_by(Inspection.created_at.desc())

    status = (request.args.get("status") or "").upper()
    if status in ("PASS", "FAIL"):
        q = q.filter(Inspection.status == status)

    date_from = request.args.get("from")
    date_to = request.args.get("to")
    if date_from:
        q = q.filter(Inspection.created_at >= date_from)
    if date_to:
        q = q.filter(Inspection.created_at <= date_to + " 23:59:59")

    inspections = q.limit(500).all()
    history_data = [i.to_history_row() for i in inspections]
    return render_template(
        "history.html",
        history=history_data,
        filters={"status": status, "from": date_from or "", "to": date_to or ""},
    )
