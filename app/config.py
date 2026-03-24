import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    APP_NAME = "Office Inventory System"
    SECRET_KEY = os.environ.get("SECRET_KEY", "office-inventory-dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
    DEFAULT_PHOTO_PATH = "uploads/placeholder-supply.svg"
    SEED_ADMIN_USERNAME = os.environ.get("SEED_ADMIN_USERNAME", "admin")
    SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "admin123")
    SEED_ERLA_USERNAME = os.environ.get("SEED_ERLA_USERNAME", "Erla")
    SEED_ERLA_PASSWORD = os.environ.get("SEED_ERLA_PASSWORD", "Erla123")
    SEED_APRIL_USERNAME = os.environ.get("SEED_APRIL_USERNAME", "April")
    SEED_APRIL_PASSWORD = os.environ.get("SEED_APRIL_PASSWORD", "April123")
