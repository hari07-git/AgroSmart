from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request, session

from .auth_helpers import login_required
from .db import db
from .models import CropPrediction, DiseasePrediction, FertilizerRecommendation, SoilRecord
from .services.disease import analyze_leaf_image
from .services.fertilizer_logic import fertilizer_recommendation
from .services.crop_ml import predict_crop
from .services.model_registry import get_active_model
from .services.weather import WeatherError, fetch_openweather_current
from .models import User

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.post("/crop/predict")
@login_required
def crop_predict():
    payload = request.get_json(silent=True) or {}
    user_id = int(session["user_id"])

    soil = SoilRecord(
        user_id=user_id,
        nitrogen=_to_float(payload.get("nitrogen")),
        phosphorus=_to_float(payload.get("phosphorus")),
        potassium=_to_float(payload.get("potassium")),
        temperature=_to_float(payload.get("temperature")),
        humidity=_to_float(payload.get("humidity")),
        rainfall=_to_float(payload.get("rainfall")),
        ph=_to_float(payload.get("ph")),
        season=str(payload.get("season") or "Kharif"),
    )
    db.session.add(soil)
    db.session.flush()

    ml = predict_crop(
        nitrogen=soil.nitrogen,
        phosphorus=soil.phosphorus,
        potassium=soil.potassium,
        temperature=soil.temperature,
        humidity=soil.humidity,
        rainfall=soil.rainfall,
        ph=soil.ph,
        season=soil.season,
    )

    predicted_crop = ml.predicted_crop or "Unknown"
    db.session.add(
        CropPrediction(
            soil_record_id=soil.id,
            predicted_crop=predicted_crop,
            model_version=ml.model_version,
            confidence=ml.confidence,
        )
    )
    db.session.commit()

    return jsonify(
        {
            "predicted_crop": predicted_crop,
            "confidence": ml.confidence,
            "model_version": ml.model_version,
        }
    )


@bp.post("/fertilizer/recommend")
@login_required
def fertilizer_recommend():
    payload = request.get_json(silent=True) or {}
    user_id = int(session["user_id"])

    crop_name = str(payload.get("crop_name") or "Rice").strip() or "Rice"
    nitrogen = _to_float(payload.get("nitrogen"))
    phosphorus = _to_float(payload.get("phosphorus"))
    potassium = _to_float(payload.get("potassium"))

    plan = fertilizer_recommendation(
        crop_name=crop_name,
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
    )

    import json

    db.session.add(
        FertilizerRecommendation(
            user_id=user_id,
            crop_name=plan["crop"],
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium,
            recommendation_json=json.dumps(plan, sort_keys=True),
        )
    )
    db.session.commit()
    return jsonify(plan)


@bp.post("/disease/predict")
@login_required
def disease_predict():
    uploaded_file = request.files.get("leaf_image")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "leaf_image file is required"}), 400

    user_id = int(session["user_id"])
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}_{Path(uploaded_file.filename).name}"
    destination = upload_dir / safe_name
    uploaded_file.save(destination)

    result = analyze_leaf_image(destination)
    active = get_active_model("disease")
    if active and result.get("model_version") == "active:model":
        result["model_version"] = active["version"]
    result["image_filename"] = safe_name

    db.session.add(
        DiseasePrediction(
            user_id=user_id,
            image_filename=safe_name,
            disease=result["disease"],
            confidence=result["confidence"],
            treatment=result["treatment"],
            prevention=result["prevention"],
            model_version=result.get("model_version", "placeholder-v1"),
        )
    )
    db.session.commit()

    return jsonify(result)


@bp.get("/weather/current")
@login_required
def weather_current():
    user_id = int(session["user_id"])
    user = db.session.get(User, user_id)
    location = (request.args.get("location") or (user.profile.location if user and user.profile else "") or "").strip()
    if not location:
        return jsonify({"error": "location is required (set it in Profile or pass ?location=...)" }), 400

    try:
        data = fetch_openweather_current(location)
    except WeatherError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(data)


@bp.post("/chatbot")
def chatbot_reply():
    payload = request.get_json(silent=True) or {}
    msg = str(payload.get("message") or "").strip()
    if not msg:
        return jsonify({"reply": "Ask me something about AgroSmart (crop, fertilizer, disease, OTP, admin)."}), 200

    text = msg.lower()

    def _contains(*words: str) -> bool:
        return any(w in text for w in words)

    # Simple, deterministic FAQ bot for demo use. For deeper support, route to admin email.
    if _contains("admin", "administrator"):
        return jsonify(
            {
                "reply": "Admin login is available from the top menu. If you need admin access or help, contact agrosmartz7@gmail.com.",
            }
        )
    if _contains("otp", "verify", "verification", "email not", "mail not", "not receiving"):
        return jsonify(
            {
                "reply": "Members receive a 6-digit OTP on registration. Check Spam/All Mail, then click 'Resend OTP'. If you still do not receive it, contact agrosmartz7@gmail.com.",
            }
        )
    if _contains("crop", "recommend", "recommendation", "npk", "ph", "season"):
        return jsonify(
            {
                "reply": "Crop Recommendation uses N, P, K, pH, season, and weather values (temperature, humidity, rainfall) to suggest a best-fit crop. Fill the form and submit to get the result and history.",
            }
        )
    if _contains("fertilizer", "urea", "dap", "mop", "npk"):
        return jsonify(
            {
                "reply": "Fertilizer Guidance uses your crop name plus N, P, K values and returns a nutrient-focused plan with steps. Use the Fertilizer service page to generate and save recommendations.",
            }
        )
    if _contains("disease", "leaf", "spot", "blight", "rust", "mildew"):
        return jsonify(
            {
                "reply": "Disease Detection works by uploading a clear leaf photo. The app shows the uploaded image, top predictions, confidence, plus treatment and prevention suggestions. If results look uncertain, retake a clearer photo and try again.",
            }
        )
    if _contains("export", "pdf", "csv", "history", "report"):
        return jsonify(
            {
                "reply": "You can view your history from Dashboard and export CSV/PDF reports. If export fails or you need a full report, contact agrosmartz7@gmail.com.",
            }
        )
    if _contains("language", "telugu", "hindi", "english"):
        return jsonify(
            {
                "reply": "Use the Language dropdown in the top bar to switch English/Telugu/Hindi across the site.",
            }
        )
    if _contains("weather", "openweather", "location"):
        return jsonify(
            {
                "reply": "Weather auto-fill can use your Profile location to fetch current weather. Set your location in Profile, then use the Weather button on forms (if available).",
            }
        )

    return jsonify(
        {
            "reply": "I can help with basic AgroSmart questions (crop, fertilizer, disease, OTP, exports, language). For deeper help, contact agrosmartz7@gmail.com.",
        }
    )


def _to_float(value) -> float:
    try:
        return float(value) if value not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0
