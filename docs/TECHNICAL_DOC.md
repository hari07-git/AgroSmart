# AgroSmart Technical Documentation

## Overview

AgroSmart is a Flask web application with an SQLite database that stores:

- users and farmer profiles
- soil input records
- crop predictions
- fertilizer recommendations
- disease predictions

The system supports both:

- UI flows via server-rendered HTML templates
- API flows via `/api/*` endpoints (session-authenticated)

## Database

SQLite database file: `agrosmart.sqlite3` (auto-created at runtime).

Tables are defined in `agrosmart/models.py` and created via `db.create_all()` in `agrosmart/__init__.py`.

## ML Hooks

### Crop Model

- Training script: `scripts/train_crop_model.py`
- Expected CSV columns: `N,P,K,temperature,humidity,rainfall,ph,season,label`
- Saved model: `models/crop_model.joblib`
- Runtime loader: `agrosmart/services/crop_ml.py`

If the model is missing or dependencies are not installed, the app falls back to rule-based recommendations.

### Disease Model

Dataset format: directory with one subfolder per class label (each contains `.jpg/.png` images).

Training scripts:

- Keras/CNN: `scripts/train_disease_model.py` -> `models/disease_model.keras` (requires TensorFlow)
- scikit-learn: `scripts/train_disease_model_sklearn.py` -> `models/disease_model.joblib` (recommended for this repo/Python)

Labels file: `models/disease_model.labels.json` (auto-written by the training script).

Runtime loader: `agrosmart/services/disease_ml.py` (loads the active admin model if present).

If the model is missing, the app falls back to placeholder detection.

### Disease Model Evaluation

Evaluate a trained `.joblib` model on a labeled dataset:

```bash
.venv/bin/python scripts/evaluate_disease_model.py --data_dir /path/to/leaf_dataset --model models/disease_model.joblib --out docs/disease_eval.json
```

## Testing

- Install dev dependencies: `pip install -r requirements-dev.txt`
- Run tests: `pytest -q`

## Admin

Admin routes are under `/admin` and require `User.is_admin = True`.

Promote a user to admin:

`python3 scripts/make_admin.py --email you@example.com`

Admin login:

- URL: `/admin/login`
- Successful admin login sets `session['admin_user_id']` (separate from normal user session).

## Model Versioning

Admin can upload and activate model artifacts under `/admin/models`.

- Crop model: `.joblib` (scikit-learn pipeline saved with joblib)
- Disease model: `.keras` (+ optional `.json` labels file)

When an active model exists in `model_artifacts`, runtime prediction uses that model instead of the default file paths.
