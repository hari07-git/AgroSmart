from __future__ import annotations

from werkzeug.security import generate_password_hash

from ..db import db, utcnow
from ..models import User


def ensure_bootstrap_admin() -> bool:
    """
    Ensure a demo admin exists (used for Render/demo deployments).
    Returns True if created/updated, False if skipped.
    """
    from flask import current_app

    if not bool(current_app.config.get("BOOTSTRAP_ADMIN", False)):
        return False

    email = str(current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
    password = str(current_app.config.get("ADMIN_PASSWORD") or "")
    name = str(current_app.config.get("ADMIN_NAME") or "AgroSmart Admin").strip() or "AgroSmart Admin"

    if not email or not password:
        return False

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True,
            email_verified=True,
            email_verified_at=utcnow(),
        )
        db.session.add(user)
        db.session.commit()
        return True

    changed = False
    if not user.is_admin:
        user.is_admin = True
        changed = True
    if user.name != name:
        user.name = name
        changed = True
    # Ensure verified (admin should never be blocked by OTP).
    if hasattr(user, "email_verified") and not bool(user.email_verified):
        user.email_verified = True
        changed = True
    if hasattr(user, "email_verified_at") and user.email_verified_at is None:
        user.email_verified_at = utcnow()
        changed = True

    # Keep password in sync for demo reliability.
    user.password_hash = generate_password_hash(password)
    changed = True

    if changed:
        db.session.commit()
    return True

