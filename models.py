from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

VALID_PERMISSIONS = (
    "fabric_comparison",
    "live_quality",
    "recipe_extraction",
    "ai_reports",
)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # "admin" | "user"
    permissions = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def permission_list(self):
        return [p for p in (self.permissions or "").split(",") if p]

    def has_permission(self, feature_name: str) -> bool:
        return self.role == "admin" or feature_name in self.permission_list()

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Inspection(db.Model):
    """A fabric-comparison inspection record. Replaces history.json."""

    __tablename__ = "inspections"

    id = db.Column(db.Integer, primary_key=True)
    comp_id = db.Column(db.String(40), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    operator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    operator = db.relationship("User")

    reference_filename = db.Column(db.String(255))
    test_filename = db.Column(db.String(255))
    ref_roi_path = db.Column(db.String(255))
    test_roi_path = db.Column(db.String(255))

    lab1_l = db.Column(db.Float)
    lab1_a = db.Column(db.Float)
    lab1_b = db.Column(db.Float)
    lab2_l = db.Column(db.Float)
    lab2_a = db.Column(db.Float)
    lab2_b = db.Column(db.Float)

    delta_e = db.Column(db.Float, nullable=False)
    similarity = db.Column(db.Float)
    confidence = db.Column(db.Float)
    status = db.Column(db.String(10), nullable=False)  # PASS | FAIL

    bar_chart = db.Column(db.String(255))
    pie_chart = db.Column(db.String(255))

    dominant1_json = db.Column(db.Text)
    dominant2_json = db.Column(db.Text)
    recipe_json = db.Column(db.Text)

    def lab1(self):
        return [self.lab1_l, self.lab1_a, self.lab1_b]

    def lab2(self):
        return [self.lab2_l, self.lab2_a, self.lab2_b]

    def to_history_row(self):
        return {
            "comp_id": self.comp_id,
            "time": self.created_at.strftime("%d-%m-%Y %H:%M"),
            "reference": self.reference_filename,
            "test": self.test_filename,
            "delta_e": self.delta_e,
            "status": self.status,
            "operator": self.operator.username if self.operator else "-",
        }


class RecipeExtraction(db.Model):
    """A single-image dye recipe extraction record."""

    __tablename__ = "recipe_extractions"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    operator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    operator = db.relationship("User")

    source_filename = db.Column(db.String(255))
    roi_path = db.Column(db.String(255))

    lab_l = db.Column(db.Float)
    lab_a = db.Column(db.Float)
    lab_b = db.Column(db.Float)

    dominant_json = db.Column(db.Text)
    recipe_json = db.Column(db.Text)

    def lab(self):
        return [self.lab_l, self.lab_a, self.lab_b]


class AppSetting(db.Model):
    """Admin-tunable key/value settings (QC thresholds, etc.)."""

    __tablename__ = "app_settings"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(255), nullable=False)

    @staticmethod
    def get(key: str, default=None):
        row = AppSetting.query.get(key)
        return row.value if row else default

    @staticmethod
    def get_float(key: str, default: float) -> float:
        row = AppSetting.query.get(key)
        if not row:
            return default
        try:
            return float(row.value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def set(key: str, value) -> None:
        row = AppSetting.query.get(key)
        if row:
            row.value = str(value)
        else:
            row = AppSetting(key=key, value=str(value))
            db.session.add(row)
        db.session.commit()
