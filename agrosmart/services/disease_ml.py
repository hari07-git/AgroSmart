from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import current_app

_MODEL: Any | None = None
_LABELS: list[str] | None = None
_MODEL_KIND: str | None = None
_MODEL_PATH: str | None = None


def predict_disease(image_path: Path) -> dict | None:
    from .model_registry import get_active_model

    active = get_active_model("disease")
    model_path = Path(active["path"]) if active else Path(current_app.config["DISEASE_MODEL_PATH"])
    if not model_path.exists():
        return None
    model_version = str(active["version"]) if active else model_path.name

    # Support either a Keras model (.keras) or a scikit-learn model (.joblib).
    ext = model_path.suffix.lower()
    if ext == ".joblib":
        out = _predict_sklearn(image_path, model_path)
        if out is None:
            return None
        out["model_version"] = model_version
        return out
    if ext != ".keras":
        return None

    try:
        import numpy as np
        from PIL import Image
    except Exception:
        return None

    try:
        import tensorflow as tf  # type: ignore
    except Exception:
        return None

    global _MODEL, _MODEL_KIND, _MODEL_PATH, _LABELS
    if _MODEL is None or _MODEL_PATH != str(model_path):
        _MODEL = tf.keras.models.load_model(model_path)
        _MODEL_KIND = "keras"
        _MODEL_PATH = str(model_path)
        _LABELS = None

    labels = _load_labels(active_labels=(active.get("labels_path") if active else None))
    image = Image.open(image_path).convert("RGB").resize((224, 224))
    arr = (np.array(image).astype("float32") / 255.0)[None, ...]

    preds = _MODEL.predict(arr, verbose=0)
    if preds is None:
        return None
    preds = preds[0]
    idx = int(preds.argmax())
    confidence = float(preds[idx])
    disease = labels[idx] if labels and idx < len(labels) else f"class_{idx}"
    top = []
    if labels:
        ranked = sorted([(labels[i] if i < len(labels) else f"class_{i}", float(preds[i])) for i in range(len(preds))], key=lambda x: x[1], reverse=True)
        top = [{"label": lab, "prob": prob} for lab, prob in ranked[:3]]
    return {"label": disease, "confidence": confidence, "top": top, "engine": "keras", "model_version": model_version}


def _load_labels(active_labels: Path | None = None) -> list[str] | None:
    global _LABELS
    if _LABELS is not None:
        return _LABELS

    labels_path = active_labels or Path(current_app.config["DISEASE_MODEL_PATH"]).with_suffix(".labels.json")
    if not labels_path.exists():
        _LABELS = None
        return None

    try:
        _LABELS = json.loads(labels_path.read_text(encoding="utf-8"))
    except Exception:
        _LABELS = None
    return _LABELS


def _predict_sklearn(image_path: Path, model_path: Path) -> dict | None:
    try:
        import joblib
    except Exception:
        return None

    from .disease_features import extract_features

    global _MODEL, _MODEL_KIND, _MODEL_PATH, _LABELS
    if _MODEL is None or _MODEL_PATH != str(model_path):
        _MODEL = joblib.load(model_path)
        _MODEL_KIND = "sklearn"
        _MODEL_PATH = str(model_path)
        _LABELS = None

    X = [extract_features(image_path)]

    pred = _MODEL.predict(X)[0]
    confidence = 0.0
    top: list[dict] = []
    if hasattr(_MODEL, "predict_proba"):
        proba = _MODEL.predict_proba(X)[0]
        confidence = float(max(proba))
        if hasattr(_MODEL, "classes_"):
            classes = [str(c) for c in list(_MODEL.classes_)]
            idx = int(proba.argmax())
            pred = classes[idx] if idx < len(classes) else str(pred)
            ranked = sorted([(classes[i] if i < len(classes) else f"class_{i}", float(proba[i])) for i in range(len(proba))], key=lambda x: x[1], reverse=True)
            top = [{"label": lab, "prob": prob} for lab, prob in ranked[:3]]

    if not top:
        top = [{"label": str(pred), "prob": float(confidence)}]

    return {"label": str(pred), "confidence": float(confidence), "top": top, "engine": "sklearn"}
