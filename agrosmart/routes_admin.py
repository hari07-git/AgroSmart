from __future__ import annotations

import csv
import io

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for, current_app
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

from .admin_helpers import admin_required
from .db import db
from .models import CropPrediction, DiseasePrediction, FertilizerRecommendation, ModelArtifact, SoilRecord, User
from .services.reporting import generate_user_pdf_report

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
@admin_required
def dashboard():
    user_count = User.query.count()
    crop_count = CropPrediction.query.count()
    fert_count = FertilizerRecommendation.query.count()
    disease_count = DiseasePrediction.query.count()
    latest_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    return render_template(
        "admin/dashboard.html",
        stats={
            "users": user_count,
            "crop_predictions": crop_count,
            "fertilizer_recommendations": fert_count,
            "disease_predictions": disease_count,
        },
        latest_users=latest_users,
    )


@bp.get("/models")
@admin_required
def models():
    rows = ModelArtifact.query.order_by(ModelArtifact.uploaded_at.desc()).limit(200).all()
    return render_template("admin/models.html", rows=rows)


@bp.get("/models/upload")
@admin_required
def model_upload():
    return render_template("admin/model_upload.html")


@bp.post("/models/upload")
@admin_required
def model_upload_post():
    kind = (request.form.get("kind") or "").strip().lower()
    version = (request.form.get("version") or "").strip()
    model_file = request.files.get("model_file")
    labels_file = request.files.get("labels_file")

    if kind not in ("crop", "disease") or not version or not model_file or not model_file.filename:
        flash("Please provide kind, version, and a model file.", "error")
        return redirect(url_for("admin.model_upload"))

    model_name = secure_filename(Path(model_file.filename).name)
    ext = Path(model_name).suffix.lower()
    if kind == "crop" and ext != ".joblib":
        flash("Crop model must be a .joblib file.", "error")
        return redirect(url_for("admin.model_upload"))
    if kind == "disease" and ext not in (".keras", ".joblib"):
        flash("Disease model must be a .keras or .joblib file.", "error")
        return redirect(url_for("admin.model_upload"))

    store = Path(current_app.config["MODEL_STORE"])
    store.mkdir(parents=True, exist_ok=True)
    final_name = f"{kind}_{version}_{uuid4().hex}_{model_name}"
    model_path = store / final_name
    model_file.save(model_path)

    labels_final = None
    if kind == "disease" and labels_file and labels_file.filename:
        labels_name = secure_filename(Path(labels_file.filename).name)
        if Path(labels_name).suffix.lower() != ".json":
            flash("Labels file must be .json (optional).", "error")
            return redirect(url_for("admin.model_upload"))
        labels_final = f"{kind}_{version}_{uuid4().hex}_{labels_name}"
        labels_file.save(store / labels_final)

    row = ModelArtifact(
        kind=kind,
        version=version,
        filename=final_name,
        labels_filename=labels_final,
        active=False,
    )
    db.session.add(row)
    db.session.commit()
    flash("Model uploaded.", "success")
    return redirect(url_for("admin.models"))


@bp.post("/models/<int:model_id>/activate")
@admin_required
def model_activate(model_id: int):
    row = ModelArtifact.query.get_or_404(model_id)
    ModelArtifact.query.filter_by(kind=row.kind, active=True).update({"active": False})
    row.active = True
    db.session.commit()
    return redirect(url_for("admin.models"))


@bp.post("/models/<int:model_id>/delete")
@admin_required
def model_delete(model_id: int):
    row = ModelArtifact.query.get_or_404(model_id)
    store = Path(current_app.config["MODEL_STORE"])
    try:
        (store / row.filename).unlink(missing_ok=True)
        if row.labels_filename:
            (store / row.labels_filename).unlink(missing_ok=True)
    except Exception:
        pass
    db.session.delete(row)
    db.session.commit()
    return redirect(url_for("admin.models"))


@bp.get("/users")
@admin_required
def users():
    rows = User.query.order_by(User.created_at.desc()).limit(200).all()
    return render_template("admin/users.html", rows=rows)


@bp.get("/users/<int:user_id>")
@admin_required
def user_detail(user_id: int):
    user = User.query.get_or_404(user_id)
    profile = user.profile

    crop_count = (
        db.session.query(CropPrediction)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .filter(SoilRecord.user_id == user_id)
        .count()
    )
    fert_count = FertilizerRecommendation.query.filter_by(user_id=user_id).count()
    disease_count = DiseasePrediction.query.filter_by(user_id=user_id).count()

    return render_template(
        "admin/user_detail.html",
        user=user,
        profile=profile,
        counts={"crop": crop_count, "fertilizer": fert_count, "disease": disease_count},
    )


@bp.post("/users/<int:user_id>/reset-password")
@admin_required
def user_reset_password(user_id: int):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password") or ""
    if len(new_password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash("Password reset.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.post("/users/<int:user_id>/delete")
@admin_required
def user_delete(user_id: int):
    user = User.query.get_or_404(user_id)

    # Remove user-owned records explicitly to avoid SQLite FK surprises.
    soil_ids = [r[0] for r in db.session.query(SoilRecord.id).filter_by(user_id=user_id).all()]
    if soil_ids:
        db.session.query(CropPrediction).filter(CropPrediction.soil_record_id.in_(soil_ids)).delete(synchronize_session=False)
    db.session.query(SoilRecord).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.query(FertilizerRecommendation).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.session.query(DiseasePrediction).filter_by(user_id=user_id).delete(synchronize_session=False)

    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin.users"))


@bp.get("/users/<int:user_id>/export.csv")
@admin_required
def user_export_csv(user_id: int):
    user = User.query.get_or_404(user_id)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["USER"])
    writer.writerow(["id", "name", "email", "is_admin", "created_at"])
    writer.writerow([user.id, user.name, user.email, user.is_admin, user.created_at])
    writer.writerow([])

    writer.writerow(["CROP_PREDICTIONS"])
    writer.writerow(["time", "crop", "season", "confidence", "model"])
    crop_rows = (
        db.session.query(CropPrediction, SoilRecord)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .filter(SoilRecord.user_id == user_id)
        .order_by(CropPrediction.created_at.desc())
        .all()
    )
    for pred, soil in crop_rows:
        writer.writerow([pred.created_at, pred.predicted_crop, soil.season, pred.confidence, pred.model_version])
    writer.writerow([])

    writer.writerow(["FERTILIZER_RECOMMENDATIONS"])
    writer.writerow(["time", "crop", "raw_n", "raw_p", "raw_k"])
    fert_rows = FertilizerRecommendation.query.filter_by(user_id=user_id).order_by(FertilizerRecommendation.created_at.desc()).all()
    for row in fert_rows:
        writer.writerow([row.created_at, row.crop_name, row.nitrogen, row.phosphorus, row.potassium])
    writer.writerow([])

    writer.writerow(["DISEASE_PREDICTIONS"])
    writer.writerow(["time", "disease", "confidence", "model", "image"])
    dis_rows = DiseasePrediction.query.filter_by(user_id=user_id).order_by(DiseasePrediction.created_at.desc()).all()
    for row in dis_rows:
        writer.writerow([row.created_at, row.disease, row.confidence, row.model_version, row.image_filename])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=user_{user_id}_history.csv"},
    )


@bp.get("/users/<int:user_id>/report.pdf")
@admin_required
def user_report_pdf(user_id: int):
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
        crop_items.append([str(pred.created_at), pred.predicted_crop, soil.season, "" if pred.confidence is None else f"{pred.confidence:.2f}", pred.model_version])

    fert_rows = FertilizerRecommendation.query.filter_by(user_id=user_id).order_by(FertilizerRecommendation.created_at.desc()).limit(20).all()
    fert_items = [[str(r.created_at), r.crop_name, "", ""] for r in fert_rows]

    dis_rows = DiseasePrediction.query.filter_by(user_id=user_id).order_by(DiseasePrediction.created_at.desc()).limit(20).all()
    disease_items = [[str(r.created_at), r.disease, r.confidence, r.model_version] for r in dis_rows]

    try:
        pdf = generate_user_pdf_report(user=user, profile=profile, crop_items=crop_items, fert_items=fert_items, disease_items=disease_items)
    except RuntimeError as exc:
        return Response(str(exc), mimetype="text/plain", status=501)

    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=user_{user_id}_report.pdf"},
    )


@bp.post("/users/<int:user_id>/toggle-admin")
@admin_required
def toggle_admin(user_id: int):
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    return redirect(url_for("admin.users"))


@bp.get("/history")
@admin_required
def history():
    crop_rows = (
        db.session.query(CropPrediction, SoilRecord)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .order_by(CropPrediction.created_at.desc())
        .limit(50)
        .all()
    )
    fert_rows = FertilizerRecommendation.query.order_by(FertilizerRecommendation.created_at.desc()).limit(50).all()
    disease_rows = DiseasePrediction.query.order_by(DiseasePrediction.created_at.desc()).limit(50).all()
    return render_template(
        "admin/history.html",
        crop_rows=crop_rows,
        fert_rows=fert_rows,
        disease_rows=disease_rows,
    )


@bp.post("/delete/crop/<int:prediction_id>")
@admin_required
def delete_crop(prediction_id: int):
    pred = CropPrediction.query.get_or_404(prediction_id)
    db.session.delete(pred)
    db.session.commit()
    return redirect(url_for("admin.history"))


@bp.post("/delete/fertilizer/<int:rec_id>")
@admin_required
def delete_fertilizer(rec_id: int):
    rec = FertilizerRecommendation.query.get_or_404(rec_id)
    db.session.delete(rec)
    db.session.commit()
    return redirect(url_for("admin.history"))


@bp.post("/delete/disease/<int:pred_id>")
@admin_required
def delete_disease(pred_id: int):
    pred = DiseasePrediction.query.get_or_404(pred_id)
    db.session.delete(pred)
    db.session.commit()
    return redirect(url_for("admin.history"))


@bp.get("/export/crop.csv")
@admin_required
def export_crop_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "created_at",
            "predicted_crop",
            "confidence",
            "model_version",
            "season",
            "nitrogen",
            "phosphorus",
            "potassium",
            "temperature",
            "humidity",
            "rainfall",
            "ph",
            "user_id",
        ]
    )
    rows = (
        db.session.query(CropPrediction, SoilRecord)
        .join(SoilRecord, CropPrediction.soil_record_id == SoilRecord.id)
        .order_by(CropPrediction.created_at.desc())
        .all()
    )
    for pred, soil in rows:
        writer.writerow(
            [
                pred.created_at,
                pred.predicted_crop,
                pred.confidence,
                pred.model_version,
                soil.season,
                soil.nitrogen,
                soil.phosphorus,
                soil.potassium,
                soil.temperature,
                soil.humidity,
                soil.rainfall,
                soil.ph,
                soil.user_id,
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=crop_predictions.csv"},
    )
