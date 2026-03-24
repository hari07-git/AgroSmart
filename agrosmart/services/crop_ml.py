from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from flask import current_app

from .model_registry import get_active_model


@dataclass(frozen=True)
class CropMlResult:
    predicted_crop: str
    confidence: float | None
    model_version: str
    used_model: bool


def predict_crop(
    *,
    nitrogen: float,
    phosphorus: float,
    potassium: float,
    temperature: float,
    humidity: float,
    rainfall: float,
    ph: float,
    season: str,
) -> CropMlResult:
    active = get_active_model("crop")
    model_path = Path(active["path"]) if active else Path(current_app.config["CROP_MODEL_PATH"])
    if not model_path.exists():
        return CropMlResult(predicted_crop="", confidence=None, model_version="rule-based-v1", used_model=False)

    try:
        import joblib
    except Exception:
        return CropMlResult(predicted_crop="", confidence=None, model_version="rule-based-v1", used_model=False)

    model = joblib.load(model_path)
    features = [[nitrogen, phosphorus, potassium, temperature, humidity, rainfall, ph, season]]
    predicted = model.predict(features)[0]

    confidence = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features)[0]
        confidence = float(max(proba))

    return CropMlResult(
        predicted_crop=str(predicted),
        confidence=confidence,
        model_version=(f"sklearn-joblib:{model_path.name}" if not active else f"sklearn:{active['version']}"),
        used_model=True,
    )
