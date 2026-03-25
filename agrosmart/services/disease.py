from pathlib import Path

from .disease_ml import predict_disease
from .disease_features import looks_healthy


DISEASE_KEYWORDS = {
    # Common dataset/field labels
    "cercospora": {
        "disease": "Cercospora Leaf Spot",
        "treatment": "Remove infected leaves, avoid overhead watering, and apply a recommended fungicide if spread increases.",
        "prevention": "Rotate crops, keep field clean, and ensure good spacing/airflow to reduce humidity near leaves.",
    },
    "bacterial_spot": {
        "disease": "Bacterial Spot",
        "treatment": "Remove heavily infected leaves and use a crop-approved bacterial control (often copper-based) if advised locally.",
        "prevention": "Use disease-free seed/seedlings, avoid splashing water, and sanitize tools.",
    },
    "early_blight": {
        "disease": "Early Blight",
        "treatment": "Remove infected foliage and apply a recommended fungicide as per label directions.",
        "prevention": "Rotate crops, avoid wet foliage, and maintain plant nutrition to reduce stress.",
    },
    "late_blight": {
        "disease": "Late Blight",
        "treatment": "Remove infected plants if severe and apply an appropriate fungicide quickly.",
        "prevention": "Avoid prolonged leaf wetness and monitor weather-driven outbreaks.",
    },
    "yellow_leaf_curl": {
        "disease": "Leaf Curl (viral)",
        "treatment": "Control whiteflies and remove severely affected plants to slow spread.",
        "prevention": "Use resistant varieties and insect-proof nets in nursery stage.",
    },
    "blight": {
        "disease": "Leaf Blight",
        "treatment": "Remove affected leaves, improve airflow, and apply a recommended fungicide.",
        "prevention": "Avoid overhead irrigation and monitor humidity-driven spread.",
    },
    "rust": {
        "disease": "Leaf Rust",
        "treatment": "Use a crop-safe fungicide and remove heavily infected plant sections.",
        "prevention": "Maintain field sanitation and avoid prolonged leaf wetness.",
    },
    "spot": {
        "disease": "Leaf Spot",
        "treatment": "Prune infected leaves and apply a broad-spectrum fungicide if needed.",
        "prevention": "Use clean irrigation practices and avoid overcrowding.",
    },
    "mildew": {
        "disease": "Powdery Mildew",
        "treatment": "Apply sulfur-based or crop-approved fungicide treatment.",
        "prevention": "Increase spacing and reduce excess moisture around foliage.",
    },
}


def analyze_leaf_image(image_path: Path) -> dict:
    ml = predict_disease(image_path)
    if ml is not None:
        disease_label = str(ml.get("label", "Unknown"))
        confidence = float(ml.get("confidence", 0.0) or 0.0)
        model_version = str(ml.get("model_version") or "unknown")
        threshold = 0.70
        top = ml.get("top") or []
        status = "ML model prediction"

        # If the model is not sure, prefer a heuristic label (more stable for demo)
        # and clearly show that it is low confidence / heuristic-adjusted.
        if confidence and confidence < threshold:
            status = "Low confidence prediction"
            healthy_prob = 0.0
            best_non_healthy_prob = 0.0
            best_non_healthy_label = ""
            if top:
                for item in top:
                    label = str(item.get("label", "")).lower()
                    prob = float(item.get("prob", 0.0) or 0.0)
                    if "healthy" in label:
                        healthy_prob = prob
                        continue
                    if prob > best_non_healthy_prob:
                        best_non_healthy_prob = prob
                        best_non_healthy_label = str(item.get("label", "") or "")

            # Only allow a "Healthy" override when:
            # 1) the image looks healthy AND
            # 2) the model also leans healthy (healthy prob clearly above best disease prob).
            #
            # This prevents cases where diseased leaves get "No treatment needed" just because
            # the model is uncertain and healthy is barely the top class.
            try:
                margin = healthy_prob - best_non_healthy_prob
                allow_healthy_override = looks_healthy(image_path) and (
                    healthy_prob >= 0.55 or margin >= 0.12
                )
                if allow_healthy_override:
                    details = _treatment_for_label("healthy")
                    return {
                        "status": "Healthy (heuristic)",
                        "disease": details["disease"],
                        "confidence": f"{confidence:.2f}",
                        "treatment": details["treatment"],
                        "prevention": details["prevention"],
                        "model_version": model_version,
                        "top_predictions": top,
                        "note": "Model confidence is low, but the image looks healthy.",
                        "raw_label": disease_label,
                    }
            except Exception:
                pass

            # Otherwise, show the most likely class (low confidence).
            likely_label = (
                best_non_healthy_label
                or (str(top[0].get("label", "")) if top else "")
                or disease_label
            )
            details = _treatment_for_label(likely_label)
            return {
                "status": status,
                "disease": details["disease"],
                "confidence": f"{confidence:.2f}",
                "treatment": details["treatment"],
                "prevention": details["prevention"],
                "model_version": model_version,
                "top_predictions": top,
                "note": "Low confidence. Use Top predictions to judge and retake the photo for better accuracy.",
                "raw_label": likely_label,
            }

        details = _treatment_for_label(disease_label)
        return {
            "status": status,
            "disease": details["disease"],
            "confidence": f"{confidence:.2f}",
            "treatment": details["treatment"],
            "prevention": details["prevention"],
            "model_version": model_version,
            "top_predictions": top,
            "note": "Prediction generated from the active model configured in Admin -> Models.",
        }

    filename = image_path.name.lower()
    for keyword, details in DISEASE_KEYWORDS.items():
        if keyword in filename:
            return {
                "status": "Fallback (filename hint)",
                "disease": details["disease"],
                "confidence": "Medium",
                "treatment": details["treatment"],
                "prevention": details["prevention"],
                "model_version": "placeholder-v1",
                "note": "No CNN model is active. This result is inferred from the filename only. For real detection, upload/activate a disease model in Admin -> Models.",
            }

    return {
        "status": "Fallback (no model)",
        "disease": "Unknown disease",
        "confidence": "Pending ML model",
        "treatment": "Upload/activate a CNN disease model (Admin -> Models) for accurate detection. As a temporary workaround, rename files with disease labels (e.g., cercospora, blight, rust) for filename-hint fallback.",
        "prevention": "Ensure field sanitation and monitor early symptoms to reduce spread.",
        "model_version": "placeholder-v1",
        "note": f"Image saved as {image_path.name}. Upload pipeline is ready for a real model.",
    }


def _treatment_for_label(label: str) -> dict:
    key = label.strip().lower()
    if "healthy" in key:
        return {
            "disease": "Healthy (no disease detected)",
            "treatment": "No treatment needed. Continue regular monitoring and maintain good irrigation and nutrition practices.",
            "prevention": "Keep field clean, avoid overwatering, and inspect leaves weekly for early symptoms.",
        }
    for keyword, details in DISEASE_KEYWORDS.items():
        if keyword in key:
            return details
    return {
        "disease": label,
        "treatment": "Follow crop-specific integrated pest management (IPM) guidelines and consult local experts.",
        "prevention": "Avoid prolonged leaf wetness and maintain clean tools and field hygiene.",
    }
