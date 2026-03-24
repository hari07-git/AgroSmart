from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, session, url_for

from .auth_helpers import login_required
from .db import db
from .models import CropPrediction, DiseasePrediction, FertilizerRecommendation, SoilRecord
from .services.advisory import build_advisory
from .services.crop_ml import predict_crop
from .services.fertilizer_logic import fertilizer_recommendation
from .services.disease import analyze_leaf_image
from .services.validation import validate_crop_inputs, validate_fertilizer_inputs
from .models import User
from .services.reporting import generate_user_pdf_report
from .services.model_registry import get_active_model

bp = Blueprint("services", __name__, url_prefix="/services")


@bp.get("/crop")
@login_required
def crop():
    return render_template("services/crop.html", result=None)


@bp.post("/crop")
@login_required
def crop_post():
    user_id = int(session["user_id"])
    nitrogen = _to_float(request.form.get("nitrogen"))
    phosphorus = _to_float(request.form.get("phosphorus"))
    potassium = _to_float(request.form.get("potassium"))
    temperature = _to_float(request.form.get("temperature"))
    humidity = _to_float(request.form.get("humidity"))
    rainfall = _to_float(request.form.get("rainfall"))
    ph = _to_float(request.form.get("ph"))
    errors = validate_crop_inputs(
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
        temperature=temperature,
        humidity=humidity,
        rainfall=rainfall,
        ph=ph,
    )
    if errors:
        for err in errors:
            flash(err, "error")
        return redirect(url_for("services.crop"))

    soil = SoilRecord(
        user_id=user_id,
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
        temperature=temperature,
        humidity=humidity,
        rainfall=rainfall,
        ph=ph,
        season=(request.form.get("season") or "Kharif").strip(),
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

    advisory = build_advisory(
        nitrogen=soil.nitrogen,
        phosphorus=soil.phosphorus,
        potassium=soil.potassium,
        temperature=soil.temperature,
        humidity=soil.humidity,
        rainfall=soil.rainfall,
        ph=soil.ph,
        season=soil.season,
        crop_name=ml.predicted_crop or "",
    )

    predicted_crop = ml.predicted_crop or advisory["recommended_crop"]["name"]
    prediction = CropPrediction(
        soil_record_id=soil.id,
        predicted_crop=predicted_crop,
        model_version=ml.model_version,
        confidence=ml.confidence,
    )
    db.session.add(prediction)
    db.session.commit()

    advisory["ml"] = {
        "used_model": ml.used_model,
        "predicted_crop": predicted_crop,
        "confidence": ml.confidence,
        "model_version": ml.model_version,
    }

    return render_template("services/crop.html", result=advisory)


@bp.get("/crop/history")
@login_required
def crop_history():
    user_id = int(session["user_id"])
    rows = (
        db.session.query(CropPrediction, SoilRecord)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .filter(SoilRecord.user_id == user_id)
        .order_by(CropPrediction.created_at.desc())
        .limit(30)
        .all()
    )
    items = []
    for pred, soil in rows:
        items.append(
            {
                "id": pred.id,
                "created_at": pred.created_at,
                "crop": pred.predicted_crop,
                "confidence": pred.confidence,
                "model_version": pred.model_version,
                "season": soil.season,
                "n": soil.nitrogen,
                "p": soil.phosphorus,
                "k": soil.potassium,
            }
        )
    return render_template("services/crop_history.html", items=items)


@bp.post("/crop/delete/<int:prediction_id>")
@login_required
def crop_delete(prediction_id: int):
    user_id = int(session["user_id"])
    row = db.session.get(CropPrediction, prediction_id)
    if row is None:
        abort(404)
    soil = db.session.get(SoilRecord, row.soil_record_id)
    if not soil or soil.user_id != user_id:
        flash("Not allowed.", "error")
        return redirect(url_for("services.crop_history"))
    db.session.delete(row)
    db.session.commit()
    flash("Deleted crop prediction.", "success")
    return redirect(url_for("services.crop_history"))


@bp.get("/fertilizer")
@login_required
def fertilizer():
    return render_template("services/fertilizer.html", result=None)


@bp.post("/fertilizer")
@login_required
def fertilizer_post():
    user_id = int(session["user_id"])
    crop_name = (request.form.get("crop_name") or "").strip() or "Rice"

    nitrogen = _to_float(request.form.get("nitrogen"))
    phosphorus = _to_float(request.form.get("phosphorus"))
    potassium = _to_float(request.form.get("potassium"))
    errors = validate_fertilizer_inputs(nitrogen=nitrogen, phosphorus=phosphorus, potassium=potassium)
    if errors:
        for err in errors:
            flash(err, "error")
        return redirect(url_for("services.fertilizer"))

    fertilizer_plan = fertilizer_recommendation(
        crop_name=crop_name,
        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,
    )
    db.session.add(
        FertilizerRecommendation(
            user_id=user_id,
            crop_name=fertilizer_plan["crop"],
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium,
            recommendation_json=json.dumps(fertilizer_plan, sort_keys=True),
        )
    )
    db.session.commit()

    return render_template("services/fertilizer.html", result=fertilizer_plan)


@bp.get("/fertilizer/history")
@login_required
def fertilizer_history():
    user_id = int(session["user_id"])
    rows = (
        FertilizerRecommendation.query.filter_by(user_id=user_id)
        .order_by(FertilizerRecommendation.created_at.desc())
        .limit(30)
        .all()
    )
    items = []
    for row in rows:
        try:
            payload = json.loads(row.recommendation_json)
        except Exception:
            payload = {"crop": row.crop_name}
        items.append(
            {
                "id": row.id,
                "created_at": row.created_at,
                "crop": payload.get("crop", row.crop_name),
                "focus": payload.get("focus", ""),
                "status": payload.get("status", ""),
                "nutrients": payload.get("nutrients_to_improve", []),
            }
        )
    return render_template("services/fertilizer_history.html", items=items)


@bp.post("/fertilizer/delete/<int:rec_id>")
@login_required
def fertilizer_delete(rec_id: int):
    user_id = int(session["user_id"])
    row = db.session.get(FertilizerRecommendation, rec_id)
    if row is None:
        abort(404)
    if row.user_id != user_id:
        flash("Not allowed.", "error")
        return redirect(url_for("services.fertilizer_history"))
    db.session.delete(row)
    db.session.commit()
    flash("Deleted fertilizer record.", "success")
    return redirect(url_for("services.fertilizer_history"))


@bp.get("/disease")
@login_required
def disease():
    return render_template("services/disease.html", result=None, model=get_active_model("disease"))


@bp.post("/disease")
@login_required
def disease_post():
    user_id = int(session["user_id"])
    uploaded_file = request.files.get("leaf_image")
    if not uploaded_file or not uploaded_file.filename:
        flash("Please upload a leaf image.", "error")
        return redirect(url_for("services.disease"))

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
    result["image_url"] = url_for("services.disease_image", filename=safe_name)

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

    return render_template("services/disease.html", result=result, model=active)


@bp.get("/disease/history")
@login_required
def disease_history():
    user_id = int(session["user_id"])
    rows = (
        DiseasePrediction.query.filter_by(user_id=user_id)
        .order_by(DiseasePrediction.created_at.desc())
        .limit(30)
        .all()
    )
    return render_template("services/disease_history.html", rows=rows)


@bp.get("/disease/image/<path:filename>")
@login_required
def disease_image(filename: str):
    user_id = int(session["user_id"])
    safe_name = Path(filename).name
    row = DiseasePrediction.query.filter_by(user_id=user_id, image_filename=safe_name).first()
    if row is None:
        abort(404)

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    path = (upload_dir / safe_name).resolve()
    if upload_dir.resolve() not in path.parents:
        abort(400)
    if not path.exists():
        abort(404)

    return send_file(path)


@bp.post("/disease/delete/<int:pred_id>")
@login_required
def disease_delete(pred_id: int):
    user_id = int(session["user_id"])
    row = db.session.get(DiseasePrediction, pred_id)
    if row is None:
        abort(404)
    if row.user_id != user_id:
        flash("Not allowed.", "error")
        return redirect(url_for("services.disease_history"))
    db.session.delete(row)
    db.session.commit()
    flash("Deleted disease record.", "success")
    return redirect(url_for("services.disease_history"))


@bp.get("/me/export.csv")
@login_required
def my_history_export_csv():
    user_id = int(session["user_id"])
    # Single CSV with three sections is easiest to open in Excel/Sheets.
    import csv
    import io
    from flask import Response

    out = io.StringIO()
    w = csv.writer(out)

    w.writerow(["CROP_PREDICTIONS"])
    w.writerow(["time", "crop", "season", "confidence", "model"])
    crop_rows = (
        db.session.query(CropPrediction, SoilRecord)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .filter(SoilRecord.user_id == user_id)
        .order_by(CropPrediction.created_at.desc())
        .limit(200)
        .all()
    )
    for pred, soil in crop_rows:
        w.writerow([pred.created_at, pred.predicted_crop, soil.season, pred.confidence, pred.model_version])

    w.writerow([])
    w.writerow(["FERTILIZER_RECOMMENDATIONS"])
    w.writerow(["time", "crop", "status", "focus"])
    fert_rows = (
        FertilizerRecommendation.query.filter_by(user_id=user_id)
        .order_by(FertilizerRecommendation.created_at.desc())
        .limit(200)
        .all()
    )
    for row in fert_rows:
        try:
            payload = json.loads(row.recommendation_json)
        except Exception:
            payload = {}
        w.writerow([row.created_at, payload.get("crop", row.crop_name), payload.get("status", ""), payload.get("focus", "")])

    w.writerow([])
    w.writerow(["DISEASE_PREDICTIONS"])
    w.writerow(["time", "disease", "confidence", "model", "image"])
    dis_rows = (
        DiseasePrediction.query.filter_by(user_id=user_id)
        .order_by(DiseasePrediction.created_at.desc())
        .limit(200)
        .all()
    )
    for row in dis_rows:
        w.writerow([row.created_at, row.disease, row.confidence, row.model_version, row.image_filename])

    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=my_history.csv"},
    )


@bp.get("/me/report.pdf")
@login_required
def my_report_pdf():
    user_id = int(session["user_id"])
    from flask import Response, current_app

    user = User.query.get_or_404(user_id)
    profile = user.profile

    crop_rows = (
        db.session.query(CropPrediction, SoilRecord)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .filter(SoilRecord.user_id == user_id)
        .order_by(CropPrediction.created_at.desc())
        .limit(20)
        .all()
    )
    crop_items = []
    for pred, soil in crop_rows:
        crop_items.append(
            [
                str(pred.created_at),
                pred.predicted_crop,
                soil.season,
                "" if pred.confidence is None else f"{pred.confidence:.2f}",
                pred.model_version,
            ]
        )

    fert_rows = (
        FertilizerRecommendation.query.filter_by(user_id=user_id)
        .order_by(FertilizerRecommendation.created_at.desc())
        .limit(20)
        .all()
    )
    fert_items = []
    for row in fert_rows:
        try:
            payload = json.loads(row.recommendation_json)
        except Exception:
            payload = {}
        fert_items.append([str(row.created_at), payload.get("crop", row.crop_name), payload.get("status", ""), payload.get("focus", "")])

    dis_rows = (
        DiseasePrediction.query.filter_by(user_id=user_id)
        .order_by(DiseasePrediction.created_at.desc())
        .limit(20)
        .all()
    )
    disease_items = []
    for row in dis_rows:
        disease_items.append([str(row.created_at), row.disease, row.confidence, row.model_version])

    try:
        pdf = generate_user_pdf_report(
            user=user,
            profile=profile,
            crop_items=crop_items,
            fert_items=fert_items,
            disease_items=disease_items,
        )
    except RuntimeError as exc:
        return Response(str(exc), mimetype="text/plain", status=501)

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=agrosmart_report.pdf"},
    )


def _to_float(value: str | None) -> float:
    try:
        return float(value) if value not in (None, "") else 0.0
    except ValueError:
        return 0.0
