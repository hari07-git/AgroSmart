from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .models import User

bp = Blueprint("admin_auth", __name__, url_prefix="/admin")


@bp.get("/login")
def login():
    return render_template("admin/login.html")


@bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    next_path = (request.args.get("next") or "/admin/").strip() or "/admin/"

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_admin or not check_password_hash(user.password_hash, password):
        flash("Invalid admin credentials.", "error")
        return redirect(url_for("admin_auth.login"))

    session["user_id"] = user.id
    session["admin_user_id"] = user.id
    flash("Admin login successful.", "success")
    return redirect(next_path)


@bp.post("/logout")
def logout():
    session.pop("admin_user_id", None)
    flash("Admin logged out.", "success")
    return redirect(url_for("admin_auth.login"))

