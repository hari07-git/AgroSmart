from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from flask import redirect, session, url_for


def login_required(handler: Callable):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return handler(*args, **kwargs)

    return wrapper
