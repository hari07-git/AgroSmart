from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a disease image classifier (scikit-learn) and save as joblib.")
    parser.add_argument("--data_dir", required=True, help="Dataset directory with subfolders per class label")
    parser.add_argument("--out", default="models/disease_model.joblib", help="Output joblib model path")
    parser.add_argument("--test_size", type=float, default=0.25, help="Holdout fraction (default 0.25)")
    args = parser.parse_args()

    # Allow running without installing the package.
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import joblib
    from sklearn.ensemble import ExtraTreesClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix

    from agrosmart.services.disease_features import extract_features

    data_dir = Path(args.data_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

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

    if len(X) < 10:
        raise SystemExit("Not enough images found to train. Provide a dataset with class subfolders and images.")

    # Robust holdout split: stratify only if it is feasible for the dataset size.
    labels_set = sorted(set(y))
    n_classes = len(labels_set)
    test_size = float(args.test_size)
    if test_size <= 0.0 or test_size >= 0.9:
        test_size = 0.25

    stratify = y
    # Stratified split requires at least 1 sample per class in the test set.
    if int(round(len(y) * test_size)) < n_classes:
        stratify = None
        # Make test set large enough to include classes (best-effort).
        test_size = min(0.5, max(test_size, (n_classes + 2) / float(len(y))))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )
    clf = ExtraTreesClassifier(
        n_estimators=1200,
        random_state=42,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced_subsample",
        n_jobs=1,
    )
    clf.fit(X_train, y_train)
    acc = float(clf.score(X_test, y_test))
    print(f"Accuracy (holdout): {acc:.4f}")

    try:
        y_pred = clf.predict(X_test)
        print("Classification report (holdout):")
        print(classification_report(y_test, y_pred, digits=4, zero_division=0))
        print("Confusion matrix (holdout):")
        print(confusion_matrix(y_test, y_pred, labels=labels_set))
    except Exception:
        pass

    joblib.dump(clf, out_path)
    (out_path.with_suffix(".labels.json")).write_text(json.dumps(labels, indent=2), encoding="utf-8")
    print(f"Saved model: {out_path}")
    print(f"Saved labels: {out_path.with_suffix('.labels.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
