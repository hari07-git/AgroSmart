from __future__ import annotations

from datetime import timedelta
import secrets
from pathlib import Path
import uuid

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .db import db
from .db import utcnow
from .models import EmailOTP, FarmerProfile, User
from .auth_helpers import login_required
from .services.emailer import send_registration_otp

bp = Blueprint("auth", __name__, url_prefix="/auth")

_OTP_PURPOSE_VERIFY = "verify_email"

def _dt_naive(dt):
    # SQLite often returns naive datetimes even when timezone=True.
    try:
        return dt.replace(tzinfo=None)
    except Exception:
        return dt


@bp.get("/register")
def register():
    return render_template("auth/register.html")


@bp.post("/register")
def register_post():
    from flask import current_app

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if not name or not email or len(password) < 6:
        flash("Please provide name, email, and a password (min 6 characters).", "error")
        return redirect(url_for("auth.register"))

    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.register"))

    if User.query.filter_by(email=email).first():
        flash("Email already registered. Please login.", "error")
        return redirect(url_for("auth.login"))

    require_otp = bool(current_app.config.get("REQUIRE_EMAIL_OTP", False))
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        email_verified=(False if require_otp else True),
        email_verified_at=(None if require_otp else utcnow()),
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(FarmerProfile(user_id=user.id))

    # Optional profile image (not mandatory)
    img = request.files.get("profile_image")
    if img and getattr(img, "filename", ""):
        saved = _save_profile_image(user_id=user.id, file_storage=img)
        if saved:
            user.profile_image_filename = saved

    otp_info = {"sent": False}
    if require_otp:
        # Create OTP and send email
        otp_info = _issue_email_otp(user)
    db.session.commit()

    if require_otp:
        session.pop("user_id", None)
        session["pending_user_id"] = user.id
        flash("Registration successful. Please verify the OTP sent to your email.", "success")
        if otp_info.get("sent"):
            flash("OTP sent. Check your email inbox (or server console in dev).", "info")
        else:
            flash("OTP email failed to send. Please check email settings and click Resend OTP.", "error")
        return redirect(url_for("auth.verify_email"))

    session["user_id"] = user.id
    session.pop("pending_user_id", None)
    flash("Registration successful.", "success")
    return redirect(url_for("main.dashboard"))


@bp.get("/login")
def login():
    return render_template("auth/login.html")


@bp.post("/login")
def login_post():
    from flask import current_app

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("auth.login"))

    require_otp = bool(current_app.config.get("REQUIRE_EMAIL_OTP", False))
    # Admin accounts should never be blocked by member OTP requirements.
    if require_otp and (not bool(getattr(user, "email_verified", False))) and (not bool(getattr(user, "is_admin", False))):
        session.pop("user_id", None)
        session["pending_user_id"] = user.id
        _issue_email_otp(user, allow_cooldown=True)
        flash("Please verify your email with the OTP we sent before logging in.", "error")
        return redirect(url_for("auth.verify_email"))

    session["user_id"] = user.id
    session.pop("pending_user_id", None)
    flash("Welcome back.", "success")
    return redirect(url_for("main.dashboard"))


@bp.post("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("main.home"))


@bp.get("/profile")
@login_required
def profile():
    user_id = int(session["user_id"])
    user = db.session.get(User, user_id)
    return render_template("auth/profile.html", user=user)


@bp.post("/profile")
@login_required
def profile_post():
    user_id = int(session["user_id"])
    user = db.session.get(User, user_id)
    if user is None:
        session.clear()
        return redirect(url_for("auth.login"))

    img = request.files.get("profile_image")
    if img and getattr(img, "filename", ""):
        saved = _save_profile_image(user_id=user.id, file_storage=img)
        if saved:
            user.profile_image_filename = saved

    location = (request.form.get("location") or "").strip()
    farm_size = request.form.get("farm_size_acres")

    if user.profile is None:
        user.profile = FarmerProfile(user_id=user.id)

    user.profile.location = location or None
    try:
        user.profile.farm_size_acres = float(farm_size) if farm_size not in (None, "") else None
    except ValueError:
        user.profile.farm_size_acres = None

    db.session.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("auth.profile"))


@bp.get("/verify-email")
def verify_email():
    from flask import current_app

    if not bool(current_app.config.get("REQUIRE_EMAIL_OTP", False)):
        return redirect(url_for("auth.login"))

    pending = session.get("pending_user_id")
    if not pending:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, int(pending))
    if user is None:
        session.pop("pending_user_id", None)
        return redirect(url_for("auth.register"))
    if bool(getattr(user, "email_verified", False)):
        session["user_id"] = user.id
        session.pop("pending_user_id", None)
        return redirect(url_for("main.dashboard"))
    return render_template("auth/verify_email.html", email=user.email)


@bp.post("/verify-email")
def verify_email_post():
    from flask import current_app

    if not bool(current_app.config.get("REQUIRE_EMAIL_OTP", False)):
        return redirect(url_for("auth.login"))

    pending = session.get("pending_user_id")
    if not pending:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, int(pending))
    if user is None:
        session.pop("pending_user_id", None)
        return redirect(url_for("auth.register"))

    code = (request.form.get("otp") or "").strip()
    if not (len(code) == 6 and code.isdigit()):
        flash("Please enter the 6-digit OTP.", "error")
        return redirect(url_for("auth.verify_email"))

    now = utcnow()
    otp = (
        EmailOTP.query.filter_by(user_id=user.id, purpose=_OTP_PURPOSE_VERIFY, consumed_at=None)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if otp is None or _dt_naive(otp.expires_at) <= _dt_naive(now):
        flash("OTP expired. Please resend OTP.", "error")
        return redirect(url_for("auth.verify_email"))

    from flask import current_app

    max_attempts = int(current_app.config.get("OTP_MAX_ATTEMPTS", 5))
    if int(otp.attempts or 0) >= max_attempts:
        flash("Too many incorrect attempts. Please resend OTP.", "error")
        return redirect(url_for("auth.verify_email"))

    if not check_password_hash(otp.code_hash, code):
        otp.attempts = int(otp.attempts or 0) + 1
        db.session.commit()
        flash("Invalid OTP. Please try again.", "error")
        return redirect(url_for("auth.verify_email"))

    otp.consumed_at = now
    user.email_verified = True
    user.email_verified_at = now
    db.session.commit()

    session["user_id"] = user.id
    session.pop("pending_user_id", None)
    flash("Email verified. Welcome!", "success")
    return redirect(url_for("main.dashboard"))


@bp.post("/verify-email/resend")
def verify_email_resend():
    from flask import current_app

    if not bool(current_app.config.get("REQUIRE_EMAIL_OTP", False)):
        return redirect(url_for("auth.login"))

    pending = session.get("pending_user_id")
    if not pending:
        return redirect(url_for("auth.login"))
    user = db.session.get(User, int(pending))
    if user is None:
        session.pop("pending_user_id", None)
        return redirect(url_for("auth.register"))

    info = _issue_email_otp(user, allow_cooldown=True, force_new=True)
    if not info.get("sent") and info.get("cooldown"):
        flash("Please wait a minute before requesting a new OTP.", "error")
    elif not info.get("sent"):
        flash("Failed to send OTP email. Check email settings and try again. (Also check Spam/All Mail.)", "error")
    else:
        flash("OTP resent. Check your email inbox (or server console in dev).", "success")
    return redirect(url_for("auth.verify_email"))


def _issue_email_otp(user: User, allow_cooldown: bool = False, force_new: bool = False) -> dict:
    """
    Create and send a 6-digit OTP for email verification.
    Returns a small status dict for UI/messages.
    """
    from flask import current_app

    now = utcnow()
    cooldown = int(current_app.config.get("OTP_RESEND_COOLDOWN_SECONDS", 60))
    expires_minutes = int(current_app.config.get("OTP_EXPIRES_MINUTES", 10))

    latest = (
        EmailOTP.query.filter_by(user_id=user.id, purpose=_OTP_PURPOSE_VERIFY, consumed_at=None)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )
    if latest and not force_new:
        # Reuse current OTP if still valid.
        if _dt_naive(latest.expires_at) > _dt_naive(now):
            if allow_cooldown and (_dt_naive(now) - _dt_naive(latest.created_at)) < timedelta(seconds=cooldown):
                return {"sent": False, "cooldown": True, "debug_code": None}
            # Resend the same code is not possible (we only store hash), so create a new one.
            force_new = True

    if latest and force_new:
        # Invalidate previous unconsumed OTPs.
        EmailOTP.query.filter_by(user_id=user.id, purpose=_OTP_PURPOSE_VERIFY, consumed_at=None).delete()

    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    otp = EmailOTP(
        user_id=user.id,
        purpose=_OTP_PURPOSE_VERIFY,
        code_hash=generate_password_hash(otp_code),
        attempts=0,
        expires_at=now + timedelta(minutes=expires_minutes),
    )
    db.session.add(otp)

    sent = False
    try:
        sent = bool(send_registration_otp(user.email, otp_code))
    except Exception:
        sent = False

    # Return OTP only in dev modes (console/testing) for usability.
    debug_code = None
    if current_app.config.get("TESTING") or str(current_app.config.get("EMAIL_DELIVERY") or "").lower() == "console":
        debug_code = otp_code
    return {"sent": sent, "cooldown": False, "debug_code": debug_code}


@bp.get("/avatar")
@login_required
def avatar():
    user_id = int(session["user_id"])
    user = db.session.get(User, user_id)
    if user is None or not user.profile_image_filename:
        return ("", 404)
    from flask import current_app

    base = Path(current_app.config["UPLOAD_FOLDER"]) / "avatars"
    path = base / user.profile_image_filename
    if not path.exists():
        return ("", 404)
    return send_file(path)


def _save_profile_image(user_id: int, file_storage) -> str | None:
    from flask import current_app

    filename = secure_filename(file_storage.filename or "")
    if not filename:
        return None
    ext = Path(filename).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        return None

    base = Path(current_app.config["UPLOAD_FOLDER"]) / "avatars"
    base.mkdir(parents=True, exist_ok=True)
    out_name = f"user{user_id}_{uuid.uuid4().hex}{ext}"
    out_path = base / out_name
    try:
        file_storage.save(out_path)
    except Exception:
        return None
    return out_name
