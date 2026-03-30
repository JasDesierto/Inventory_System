from hmac import compare_digest
from secrets import token_urlsafe
from urllib.parse import urljoin, urlsplit

from flask import abort, g, request, session


CSRF_SESSION_KEY = "_csrf_token"


def ensure_request_nonce():
    # A per-request nonce lets the browser trust only the scripts we rendered.
    g.csp_nonce = token_urlsafe(16)


def get_csp_nonce():
    return getattr(g, "csp_nonce", "")


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf():
    # The app accepts the CSRF token from normal forms and from JS requests that
    # send it in a custom header.
    expected_token = session.get(CSRF_SESSION_KEY)
    submitted_token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")

    if not expected_token or not submitted_token:
        abort(400, description="Your session expired. Refresh the page and try again.")
    if not compare_digest(expected_token, submitted_token):
        abort(400, description="The security token for this request is invalid.")


def is_safe_redirect_target(target):
    # Post-login redirects are limited to same-origin URLs to avoid open
    # redirect issues.
    if not target:
        return False

    host_url = request.host_url
    test_url = urlsplit(urljoin(host_url, target))
    reference_url = urlsplit(host_url)
    return test_url.scheme in {"http", "https"} and test_url.netloc == reference_url.netloc


def validate_password_strength(password):
    # Password rules are intentionally minimal but enforce length plus mixed
    # character classes for staff-created accounts.
    password = password or ""
    if len(password) < 12:
        return "Password must be at least 12 characters long."
    if not any(character.isalpha() for character in password):
        return "Password must include at least one letter."
    if not any(character.isdigit() for character in password):
        return "Password must include at least one number."
    return None


def validate_runtime_security(app):
    # Production startup fails fast when core security settings are missing so
    # deployment mistakes do not quietly reach users.
    if not app.config.get("IS_PRODUCTION"):
        return

    secret_key = app.config.get("SECRET_KEY", "")
    if not secret_key or secret_key == "office-inventory-dev-key":
        raise RuntimeError("Production requires a unique SECRET_KEY.")
    if len(secret_key) < 32:
        raise RuntimeError("Production SECRET_KEY must be at least 32 characters long.")
    if not app.config.get("SESSION_COOKIE_SECURE"):
        raise RuntimeError("Production requires SESSION_COOKIE_SECURE=1.")
    if not app.config.get("TRUSTED_HOSTS"):
        raise RuntimeError("Production requires TRUSTED_HOSTS to be configured.")


def build_csp_header():
    # Script execution is locked down with a request-scoped nonce so inline
    # handlers are unnecessary in templates.
    nonce = get_csp_nonce()
    directives = {
        "default-src": ["'self'"],
        "script-src": ["'self'", f"'nonce-{nonce}'", "https://cdn.jsdelivr.net"],
        "style-src": ["'self'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:"],
        "media-src": ["'self'", "blob:"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "object-src": ["'none'"],
    }
    return "; ".join(
        f"{directive} {' '.join(sources)}" for directive, sources in directives.items()
    )
