from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a crop prediction model (RandomForest) and save as joblib.")
    parser.add_argument("--data", required=True, help="CSV file with columns: N,P,K,temperature,humidity,rainfall,ph,season,label")
    parser.add_argument("--out", default="models/crop_model.joblib", help="Output model path")
    args = parser.parse_args()

    import joblib
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder

    data_path = Path(args.data)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(data_path)
    required = ["N", "P", "K", "temperature", "humidity", "rainfall", "ph", "season", "label"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing columns in CSV: {missing}")

    X = df[["N", "P", "K", "temperature", "humidity", "rainfall", "ph", "season"]]
    y = df["label"]

    pre = ColumnTransformer(
        transformers=[
            ("season", OneHotEncoder(handle_unknown="ignore"), ["season"]),
        ],
        remainder="passthrough",
    )

    model = RandomForestClassifier(
        n_estimators=250,
        random_state=42,
        class_weight=None,
        n_jobs=-1,
    )

    pipeline = Pipeline([("pre", pre), ("model", model)])

    # Small datasets often can't be split with stratification.
    n_samples = int(len(df))
    n_classes = int(y.nunique())
    can_split = n_samples >= 2 * n_classes and y.value_counts().min() >= 2

    if can_split:
        # Ensure both train and test contain every class at least once.
        # n_test must be >= n_classes and n_train must be >= n_classes.
        min_test = n_classes
        max_test = n_samples - n_classes
        desired_test = max(int(round(0.2 * n_samples)), min_test)
        n_test = min(max(desired_test, min_test), max_test)
        test_size = n_test / float(n_samples)

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=42,
            stratify=y,
        )
        pipeline.fit(X_train, y_train)
        accuracy = float(pipeline.score(X_test, y_test))
        print(f"Accuracy (holdout): {accuracy:.4f}")
    else:
        pipeline.fit(X, y)
        print("Holdout accuracy skipped (dataset too small for stratified split).")

    joblib.dump(pipeline, out_path)
    print(f"Saved model: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
