import logging
import os
from logging.handlers import RotatingFileHandler

import click
from flask import Flask, jsonify, render_template
from flask_login import current_user
from werkzeug.exceptions import HTTPException

import config as config_module
from config import get_config
from extensions import csrf, db, login_manager
from models import User


def _configure_logging(app: Flask) -> None:
    log_dir = os.path.join(config_module.BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, "denim_qc.log"), maxBytes=2_000_000, backupCount=5
    )
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)
    level = logging.DEBUG if app.debug else logging.INFO

    app.logger.setLevel(level)
    app.logger.addHandler(handler)
    logging.getLogger().setLevel(level)
    logging.getLogger().addHandler(handler)


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    _configure_logging(app)

    for folder_key in ("UPLOAD_FOLDER", "ROI_FOLDER", "RESULT_FOLDER", "SAVED_REPORTS_FOLDER"):
        os.makedirs(app.config[folder_key], exist_ok=True)
    os.makedirs(os.path.join(config_module.BASE_DIR, "instance"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from blueprints.admin import admin_bp
    from blueprints.api import api_bp
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.inspection import inspection_bp
    from blueprints.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inspection_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(reports_bp)

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}

    _register_error_handlers(app)
    _register_cli(app)

    with app.app_context():
        db.create_all()

    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/error.html", code=403, message="You don't have access to this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/error.html", code=404, message="Page not found."), 404

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("errors/error.html", code=413, message="Uploaded file is too large."), 413

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error: %s", e)
        return render_template("errors/error.html", code=500, message="Something went wrong on our end."), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        return render_template("errors/error.html", code=e.code, message=e.description), e.code


def _register_cli(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, password):
        """Create (or promote) an admin user: flask create-admin"""
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username, role="admin")
            db.session.add(user)
        else:
            user.role = "admin"
        user.set_password(password)
        db.session.commit()
        click.echo(f"Admin user '{username}' is ready.")


app = create_app()

if __name__ == "__main__":
    # Never run with debug=True outside local development.
    # Use `flask run` (dev) or waitress-serve (prod) instead of this
    # for anything beyond a quick local smoke test.
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
