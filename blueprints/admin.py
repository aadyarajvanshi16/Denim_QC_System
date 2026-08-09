import logging

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import admin_required
from extensions import db
from models import VALID_PERMISSIONS, AppSetting, User

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_required
def panel():
    users = User.query.order_by(User.username).all()
    thresholds = {
        "pass": AppSetting.get_float(
            "delta_e_pass_threshold", current_app.config["DELTA_E_PASS_THRESHOLD"]
        ),
        "acceptable": AppSetting.get_float(
            "delta_e_acceptable_threshold", current_app.config["DELTA_E_ACCEPTABLE_THRESHOLD"]
        ),
    }
    return render_template(
        "admin.html", users=users, permissions=VALID_PERMISSIONS, thresholds=thresholds
    )


@admin_bp.route("/create_user", methods=["POST"])
@login_required
@admin_required
def create_user():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    selected_permissions = [p for p in request.form.getlist("permissions") if p in VALID_PERMISSIONS]

    if len(username) < 3:
        flash("Username must be at least 3 characters.", "danger")
        return redirect(url_for("admin.panel"))
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "danger")
        return redirect(url_for("admin.panel"))
    if User.query.filter_by(username=username).first():
        flash(f"Username '{username}' already exists.", "danger")
        return redirect(url_for("admin.panel"))

    user = User(username=username, role="user", permissions=",".join(selected_permissions))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    logger.info("Admin '%s' created user '%s'.", current_user.username, username)
    flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/users/<int:user_id>/revoke", methods=["POST"])
@login_required
@admin_required
def revoke_access(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Cannot revoke an admin account this way.", "danger")
        return redirect(url_for("admin.panel"))

    user.permissions = ""
    db.session.commit()
    logger.info("Admin '%s' revoked all permissions for '%s'.", current_user.username, user.username)
    flash(f"All access revoked for '{user.username}'.", "warning")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You can't delete your own account.", "danger")
        return redirect(url_for("admin.panel"))
    if user.role == "admin":
        flash("Cannot delete another admin account from here.", "danger")
        return redirect(url_for("admin.panel"))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    logger.info("Admin '%s' deleted user '%s'.", current_user.username, username)
    flash(f"User '{username}' deleted.", "success")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/settings/thresholds", methods=["POST"])
@login_required
@admin_required
def update_thresholds():
    try:
        pass_threshold = float(request.form["pass_threshold"])
        acceptable_threshold = float(request.form["acceptable_threshold"])
    except (KeyError, ValueError):
        flash("Thresholds must be numbers.", "danger")
        return redirect(url_for("admin.panel"))

    if not (0 < pass_threshold < acceptable_threshold):
        flash("Pass threshold must be positive and less than the acceptable threshold.", "danger")
        return redirect(url_for("admin.panel"))

    AppSetting.set("delta_e_pass_threshold", pass_threshold)
    AppSetting.set("delta_e_acceptable_threshold", acceptable_threshold)
    flash("QC thresholds updated.", "success")
    return redirect(url_for("admin.panel"))
