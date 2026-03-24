from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from flask import redirect, request, session, url_for

from .db import db
from .models import User


def admin_required(handler: Callable):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        admin_user_id = session.get("admin_user_id")
        if not admin_user_id:
            return redirect(url_for("admin_auth.login", next=request.path))

        user = db.session.get(User, int(admin_user_id))
        if not user or not user.is_admin:
            session.pop("admin_user_id", None)
            return redirect(url_for("admin_auth.login", next=request.path))
        return handler(*args, **kwargs)

    return wrapper
