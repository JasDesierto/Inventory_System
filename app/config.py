import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    APP_NAME = "Office Inventory System"
    SECRET_KEY = os.environ.get("SECRET_KEY", "office-inventory-dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    UPLOAD_FOLDER = str(BASE_DIR.parent / "instance" / "uploads")
    PROTECTED_UPLOAD_PREFIX = "protected_uploads/"
    DEFAULT_PHOTO_PATH = "uploads/placeholder-supply.svg"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SEED_ADMIN_USERNAME = os.environ.get("SEED_ADMIN_USERNAME", "admin")
    SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD")
    SEED_ERLA_USERNAME = os.environ.get("SEED_ERLA_USERNAME", "Erla")
    SEED_ERLA_PASSWORD = os.environ.get("SEED_ERLA_PASSWORD")
    SEED_APRIL_USERNAME = os.environ.get("SEED_APRIL_USERNAME", "April")
    SEED_APRIL_PASSWORD = os.environ.get("SEED_APRIL_PASSWORD")
