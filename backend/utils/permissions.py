from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def require_permission(code: str):
    def decorator(fn):
        @login_required
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if hasattr(current_user, "has_permission") and current_user.has_permission(
                code
            ):
                return fn(*args, **kwargs)
            return abort(403)

        return wrapper

    return decorator
