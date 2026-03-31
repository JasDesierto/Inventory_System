import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _env_bool(name, default=False):
    # Environment parsing is kept forgiving so missing or invalid values fall
    # back to safe defaults during deployment.
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default=0):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_list(name):
    value = os.environ.get(name, "")
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _default_trusted_hosts():
    configured_hosts = _env_list("TRUSTED_HOSTS")
    if configured_hosts:
        return configured_hosts

    render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
    return [render_hostname] if render_hostname else None


class Config:
    # One central config object drives both local SQLite usage and hosted
    # deployments that inject environment variables.
    APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
    IS_PRODUCTION = APP_ENV == "production"
    APP_NAME = "Office Inventory System"
    SECRET_KEY = os.environ.get("SECRET_KEY") or ("office-inventory-dev-key" if not IS_PRODUCTION else "")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_SEED_ON_START = _env_bool("AUTO_SEED_ON_START", False)
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    UPLOAD_FOLDER = str(BASE_DIR.parent / "instance" / "uploads")
    PROTECTED_UPLOAD_PREFIX = "protected_uploads/"
    DEFAULT_PHOTO_PATH = "uploads/placeholder-supply.svg"
    SESSION_COOKIE_NAME = "__Host-inventory_session" if IS_PRODUCTION else "inventory_session"
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", IS_PRODUCTION)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    SESSION_REFRESH_EACH_REQUEST = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    PREFERRED_URL_SCHEME = "https" if SESSION_COOKIE_SECURE else "http"
    ALLOW_SELF_SIGNUP = _env_bool("ALLOW_SELF_SIGNUP", not IS_PRODUCTION)
    TRUSTED_HOSTS = _default_trusted_hosts()
    PROXY_FIX_X_FOR = _env_int("PROXY_FIX_X_FOR", 0)
    PROXY_FIX_X_PROTO = _env_int("PROXY_FIX_X_PROTO", 0)
    PROXY_FIX_X_HOST = _env_int("PROXY_FIX_X_HOST", 0)
    PROXY_FIX_X_PORT = _env_int("PROXY_FIX_X_PORT", 0)
    PROXY_FIX_X_PREFIX = _env_int("PROXY_FIX_X_PREFIX", 0)
    AUTH_RATE_LIMIT_ATTEMPTS = _env_int("AUTH_RATE_LIMIT_ATTEMPTS", 5)
    AUTH_RATE_LIMIT_WINDOW_SECONDS = _env_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", 900)
    SIGNUP_RATE_LIMIT_ATTEMPTS = _env_int("SIGNUP_RATE_LIMIT_ATTEMPTS", 5)
    SIGNUP_RATE_LIMIT_WINDOW_SECONDS = _env_int("SIGNUP_RATE_LIMIT_WINDOW_SECONDS", 3600)
    SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD")
