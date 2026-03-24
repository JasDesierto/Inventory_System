from pathlib import Path

from flask import Flask, redirect, render_template, url_for

from .cli import register_cli
from .config import Config
from .extensions import db, login_manager


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .auth import auth_bp
    from .inventory import inventory_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

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

    @app.context_processor
    def inject_shell():
        return {"app_name": app.config["APP_NAME"]}

    register_cli(app)

    with app.app_context():
        db.create_all()

    return app
