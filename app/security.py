from collections import defaultdict, deque
from hmac import compare_digest
from secrets import token_urlsafe
from threading import Lock
from time import time
from urllib.parse import urljoin, urlsplit

from flask import abort, current_app, g, request, session


CSRF_SESSION_KEY = "_csrf_token"
_auth_events = defaultdict(deque)
_auth_events_lock = Lock()


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


def _client_address():
    return (request.remote_addr or "unknown").strip().lower()


def _rate_limit_key(scope, identifier):
    return f"{scope}:{identifier.strip().lower() or '<empty>'}"


def _prune_auth_events(bucket, now, window_seconds):
    cutoff = now - max(window_seconds, 1)
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()


def _retry_after_seconds(bucket, now, window_seconds):
    if not bucket:
        return 0
    expires_at = bucket[0] + max(window_seconds, 1)
    return max(int(expires_at - now), 0)


def _is_rate_limited(scope, identifier, *, limit, window_seconds):
    now = time()
    key = _rate_limit_key(scope, identifier)
    with _auth_events_lock:
        bucket = _auth_events[key]
        _prune_auth_events(bucket, now, window_seconds)
        if len(bucket) < max(limit, 1):
            return 0
        return _retry_after_seconds(bucket, now, window_seconds)


def _record_rate_limit_event(scope, identifier, *, window_seconds):
    now = time()
    key = _rate_limit_key(scope, identifier)
    with _auth_events_lock:
        bucket = _auth_events[key]
        _prune_auth_events(bucket, now, window_seconds)
        bucket.append(now)


def _clear_rate_limit_events(scope, identifier):
    key = _rate_limit_key(scope, identifier)
    with _auth_events_lock:
        _auth_events.pop(key, None)


def format_retry_after(retry_after_seconds):
    retry_after_seconds = max(int(retry_after_seconds or 0), 0)
    minutes, seconds = divmod(retry_after_seconds, 60)
    if minutes and seconds:
        return f"{minutes} minute(s) and {seconds} second(s)"
    if minutes:
        return f"{minutes} minute(s)"
    return f"{max(seconds, 1)} second(s)"


def login_retry_after(username):
    attempts = current_app.config["AUTH_RATE_LIMIT_ATTEMPTS"]
    window_seconds = current_app.config["AUTH_RATE_LIMIT_WINDOW_SECONDS"]
    normalized_username = (username or "").strip().lower() or "<empty>"
    return max(
        _is_rate_limited("login-ip", _client_address(), limit=attempts, window_seconds=window_seconds),
        _is_rate_limited("login-user", normalized_username, limit=attempts, window_seconds=window_seconds),
    )


def register_login_failure(username):
    window_seconds = current_app.config["AUTH_RATE_LIMIT_WINDOW_SECONDS"]
    normalized_username = (username or "").strip().lower() or "<empty>"
    _record_rate_limit_event("login-ip", _client_address(), window_seconds=window_seconds)
    _record_rate_limit_event("login-user", normalized_username, window_seconds=window_seconds)


def clear_login_failures(username):
    normalized_username = (username or "").strip().lower() or "<empty>"
    _clear_rate_limit_events("login-ip", _client_address())
    _clear_rate_limit_events("login-user", normalized_username)


def consume_signup_attempt():
    attempts = current_app.config["SIGNUP_RATE_LIMIT_ATTEMPTS"]
    window_seconds = current_app.config["SIGNUP_RATE_LIMIT_WINDOW_SECONDS"]
    retry_after = _is_rate_limited("signup-ip", _client_address(), limit=attempts, window_seconds=window_seconds)
    if retry_after:
        return retry_after
    _record_rate_limit_event("signup-ip", _client_address(), window_seconds=window_seconds)
    return 0


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
