from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    # Route-level authorization stays small and readable by delegating the
    # role check to a decorator.
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(403)
            if current_user.role not in roles:
                return abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator
