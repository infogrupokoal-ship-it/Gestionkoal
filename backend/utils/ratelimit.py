import time
from functools import wraps

from flask import current_app, jsonify, request, session

_BUCKETS = {}


def rate_limit(calls: int, per_seconds: int, key_fn=None):
    """Simple rate limit decorator (in-memory, per-process).
    Not for multi-instance prod use. Key default = client IP + endpoint.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                # No limitar métodos idempotentes
                if request.method in ("GET", "HEAD", "OPTIONS"):
                    return fn(*args, **kwargs)
                # Excepción específica: no contar intentos sin CSRF válido en auth.login
                if request.method == "POST" and request.endpoint == "auth.login":
                    form_token = request.form.get("csrf_token")
                    session_token = session.get("csrf_token")
                    if (
                        not form_token
                        or not session_token
                        or form_token != session_token
                    ):
                        return fn(*args, **kwargs)

                now = time.time()
                key_base = (
                    key_fn() if callable(key_fn) else request.remote_addr or "anon"
                )
                key = f"{key_base}:{request.endpoint}"
                window_start = now - per_seconds
                bucket = _BUCKETS.setdefault(key, [])
                # prune old
                while bucket and bucket[0] < window_start:
                    bucket.pop(0)
                if len(bucket) >= calls:
                    current_app.logger.warning(f"Rate limited: {key}")
                    return jsonify({"ok": False, "error": "rate_limited"}), 429
                bucket.append(now)
            except Exception:
                # fail-open to avoid breaking endpoint
                current_app.logger.warning(
                    "Rate limiter error; allowing request", exc_info=True
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
