from __future__ import annotations

from sqlalchemy import text

from .db import db


def ensure_schema() -> None:
    # Minimal SQLite migrations: add columns that were introduced after initial scaffold.
    # Only run these on SQLite. On Postgres/MySQL, use proper migrations or rely on create_all().
    try:
        if db.engine.dialect.name != "sqlite":
            return
    except Exception:
        return
    _ensure_users_is_admin()
    _ensure_users_email_verified()
    _ensure_users_profile_image()


def _ensure_users_is_admin() -> None:
    try:
        rows = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
        cols = {r[1] for r in rows}
        if "is_admin" not in cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
            db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_users_email_verified() -> None:
    try:
        rows = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
        cols = {r[1] for r in rows}
        if "email_verified" not in cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"))
        if "email_verified_at" not in cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN email_verified_at DATETIME"))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _ensure_users_profile_image() -> None:
    try:
        rows = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
        cols = {r[1] for r in rows}
        if "profile_image_filename" not in cols:
            db.session.execute(text("ALTER TABLE users ADD COLUMN profile_image_filename VARCHAR(255)"))
            db.session.commit()
    except Exception:
        db.session.rollback()
