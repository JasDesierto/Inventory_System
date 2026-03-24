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
    expected_token = session.get(CSRF_SESSION_KEY)
    submitted_token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")

    if not expected_token or not submitted_token:
        abort(400, description="Your session expired. Refresh the page and try again.")
    if not compare_digest(expected_token, submitted_token):
        abort(400, description="The security token for this request is invalid.")


def is_safe_redirect_target(target):
    if not target:
        return False

    host_url = request.host_url
    test_url = urlsplit(urljoin(host_url, target))
    reference_url = urlsplit(host_url)
    return test_url.scheme in {"http", "https"} and test_url.netloc == reference_url.netloc


def build_csp_header():
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
