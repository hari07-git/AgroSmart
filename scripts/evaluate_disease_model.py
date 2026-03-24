from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a trained disease model on a labeled folder dataset.")
    parser.add_argument("--data_dir", required=True, help="Dataset dir with subfolders per class")
    parser.add_argument("--model", required=True, help="Path to .joblib model")
    parser.add_argument("--out", default="docs/disease_eval.json", help="Output JSON report path")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import joblib
    from sklearn.metrics import classification_report, confusion_matrix

    from agrosmart.services.disease_features import extract_features

    data_dir = Path(args.data_dir)
    model_path = Path(args.model)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists():
        raise SystemExit(f"data_dir not found: {data_dir}")
    if not model_path.exists():
        raise SystemExit(f"model not found: {model_path}")

    clf = joblib.load(model_path)

    X: list[list[float]] = []
    y: list[str] = []

    class_dirs = [p for p in data_dir.iterdir() if p.is_dir()]
    class_dirs.sort(key=lambda p: p.name.lower())
    labels = [p.name for p in class_dirs]

    for class_dir in class_dirs:
        for img in class_dir.rglob("*"):
            if img.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            try:
                X.append(extract_features(img))
                y.append(class_dir.name)
            except Exception:
                continue

    if not X:
        raise SystemExit("No images found to evaluate.")

    y_pred = clf.predict(X)
    report = classification_report(y, y_pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, y_pred, labels=labels).tolist()

    acc = float(report.get("accuracy") or 0.0)
    payload = {
        "model": str(model_path),
        "data_dir": str(data_dir),
        "labels": labels,
        "n_samples": len(y),
        "accuracy": acc,
        "confusion_matrix": cm,
        "classification_report": report,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved: {out_path}")
    print(f"Accuracy: {acc:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

