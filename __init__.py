from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev-secret-key"

    db.init_app(app)

    try:
        from .routes import register_routes
    except ImportError:
        from routes import register_routes

    register_routes(app)

    with app.app_context():
        try:
            from .models import Supply, StockTransaction
        except ImportError:
            from models import Supply, StockTransaction

        db.create_all()

    return app
