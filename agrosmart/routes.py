from __future__ import annotations

from flask import Blueprint, redirect, render_template, session, url_for

from .db import db
from .models import CropPrediction, DiseasePrediction, FertilizerRecommendation, SoilRecord, User
from .services.model_registry import get_active_model

bp = Blueprint("main", __name__)


@bp.get("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return render_template("public_home.html")


@bp.get("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    user_id = int(session["user_id"])
    user = db.session.get(User, user_id)

    crop_count = (
        db.session.query(CropPrediction)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .filter(SoilRecord.user_id == user_id)
        .count()
    )
    fert_count = FertilizerRecommendation.query.filter_by(user_id=user_id).count()
    disease_count = DiseasePrediction.query.filter_by(user_id=user_id).count()

    last_crop = (
        db.session.query(CropPrediction, SoilRecord)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .filter(SoilRecord.user_id == user_id)
        .order_by(CropPrediction.created_at.desc())
        .first()
    )
    last_fert = (
        FertilizerRecommendation.query.filter_by(user_id=user_id)
        .order_by(FertilizerRecommendation.created_at.desc())
        .first()
    )
    last_disease = (
        DiseasePrediction.query.filter_by(user_id=user_id)
        .order_by(DiseasePrediction.created_at.desc())
        .first()
    )

    crop_model = get_active_model("crop")
    disease_model = get_active_model("disease")

    profile = user.profile if user else None
    location = (profile.location if profile else None) or ""

    return render_template(
        "dashboard.html",
        stats={
            "crop": crop_count,
            "fertilizer": fert_count,
            "disease": disease_count,
        },
        last={
            "crop": last_crop,
            "fertilizer": last_fert,
            "disease": last_disease,
        },
        models={
            "crop": crop_model,
            "disease": disease_model,
        },
        profile={
            "location": location,
            "farm_size_acres": (profile.farm_size_acres if profile else None),
        },
    )
