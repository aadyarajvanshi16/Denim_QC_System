from functools import wraps

from flask import abort, redirect, url_for
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=None))
        if current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)

    return decorated


def permission_required(feature_name: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user.has_permission(feature_name):
                abort(403)
            return f(*args, **kwargs)

        return decorated

    return decorator
