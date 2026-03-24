from __future__ import annotations

from sqlalchemy import UniqueConstraint

from .db import db, utcnow


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    profile_image_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    profile = db.relationship("FarmerProfile", back_populates="user", uselist=False, cascade="all,delete")


class EmailOTP(db.Model):
    __tablename__ = "email_otps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = db.Column(db.String(32), nullable=False, default="verify_email")
    code_hash = db.Column(db.String(255), nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class FarmerProfile(db.Model):
    __tablename__ = "farmer_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_farmer_profiles_user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    farm_size_acres = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", back_populates="profile")


class SoilRecord(db.Model):
    __tablename__ = "soil_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    season = db.Column(db.String(32), nullable=False)


class CropPrediction(db.Model):
    __tablename__ = "crop_predictions"

    id = db.Column(db.Integer, primary_key=True)
    soil_record_id = db.Column(db.Integer, db.ForeignKey("soil_records.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    predicted_crop = db.Column(db.String(120), nullable=False)
    model_version = db.Column(db.String(64), nullable=False, default="rule-based-v1")
    confidence = db.Column(db.Float, nullable=True)


class FertilizerRecommendation(db.Model):
    __tablename__ = "fertilizer_recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    crop_name = db.Column(db.String(120), nullable=False)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    recommendation_json = db.Column(db.Text, nullable=False)


class DiseasePrediction(db.Model):
    __tablename__ = "disease_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    image_filename = db.Column(db.String(255), nullable=False)
    disease = db.Column(db.String(120), nullable=False)
    confidence = db.Column(db.String(64), nullable=False)
    treatment = db.Column(db.Text, nullable=False)
    prevention = db.Column(db.Text, nullable=False)
    model_version = db.Column(db.String(64), nullable=False, default="placeholder-v1")


class ModelArtifact(db.Model):
    __tablename__ = "model_artifacts"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(32), nullable=False)  # crop | disease
    version = db.Column(db.String(64), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    labels_filename = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
