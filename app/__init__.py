from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix

from .cli import register_cli, seed_database
from .config import Config
from .extensions import db, login_manager
from .security import (
    build_csp_header,
    ensure_request_nonce,
    get_csp_nonce,
    get_csrf_token,
    validate_runtime_security,
    validate_csrf,
)
from .utils.uploads import migrate_public_uploads, photo_url_for


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config)
    validate_runtime_security(app)

    if any(
        app.config.get(setting, 0) > 0
        for setting in (
            "PROXY_FIX_X_FOR",
            "PROXY_FIX_X_PROTO",
            "PROXY_FIX_X_HOST",
            "PROXY_FIX_X_PORT",
            "PROXY_FIX_X_PREFIX",
        )
    ):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config["PROXY_FIX_X_FOR"],
            x_proto=app.config["PROXY_FIX_X_PROTO"],
            x_host=app.config["PROXY_FIX_X_HOST"],
            x_port=app.config["PROXY_FIX_X_PORT"],
            x_prefix=app.config["PROXY_FIX_X_PREFIX"],
        )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def apply_request_security():
        ensure_request_nonce()
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            validate_csrf()

    @app.after_request
    def apply_response_security(response):
        if request.endpoint != "static":
            response.headers["Content-Security-Policy"] = build_csp_header()
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "same-origin"
            response.headers["Permissions-Policy"] = "camera=(self)"
            response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
            response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
            response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            if app.config.get("SESSION_COOKIE_SECURE"):
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if request.endpoint != "static" and current_user.is_authenticated:
            # Authenticated pages and protected images should not be cached on shared machines.
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    from .auth import auth_bp
    from .inventory import inventory_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    @app.get("/healthz")
    def healthcheck():
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200

    @app.errorhandler(403)
    def forbidden(_error):
        return (
            render_template(
                "error.html",
                error_code=403,
                title="Access denied",
                message="Your account does not have permission to open this page.",
            ),
            403,
        )

    @app.errorhandler(400)
    def bad_request(error):
        return (
            render_template(
                "error.html",
                error_code=400,
                title="Bad request",
                message=getattr(error, "description", "The request could not be processed."),
            ),
            400,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_template(
                "error.html",
                error_code=404,
                title="Page not found",
                message="The page you requested does not exist.",
            ),
            404,
        )

    @app.errorhandler(413)
    def payload_too_large(_error):
        return (
            render_template(
                "error.html",
                error_code=413,
                title="File too large",
                message="The uploaded file exceeds the allowed size limit.",
            ),
            413,
        )

    @app.context_processor
    def inject_shell():
        return {
            "app_name": app.config["APP_NAME"],
            "allow_self_signup": app.config["ALLOW_SELF_SIGNUP"],
            "csrf_token": get_csrf_token,
            "csp_nonce": get_csp_nonce(),
            "photo_url_for": photo_url_for,
        }

    register_cli(app)

    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if inspector.has_table("users"):
            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if "avatar_path" not in user_columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(255)"))
                db.session.commit()
        from .models import Supply

        migrate_public_uploads(db, Supply)
        if app.config.get("AUTO_SEED_ON_START") and User.query.count() == 0:
            seed_database(app)
            app.logger.info("Initial database seed completed during startup.")

    return app
