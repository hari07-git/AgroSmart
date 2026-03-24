# AgroSmart

AgroSmart is a starter web application for the mini project:
"AgroSmart - Smart Crop Advisory and Disease Detection System."

This version implements the milestone modules end-to-end:

- User registration, login, and farmer profile
- Crop recommendation with an ML hook (RandomForest) and fallback logic
- Fertilizer recommendation with history and nutrient status chart
- Leaf disease detection with a CNN/Keras hook (when a model exists) and fallback logic
- REST APIs for crop, fertilizer, and disease flows
- SQLite history storage for predictions and recommendations

## Tech Stack

- Python 3.13+
- Flask
- SQLite (via SQLAlchemy)

## Project Structure

```text
AgroSmart/
├── app.py
├── requirements.txt
├── requirements-ml.txt
├── requirements-dev.txt
├── agrosmart/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── routes.py
│   ├── routes_api.py
│   ├── routes_auth.py
│   ├── routes_services.py
│   ├── services/
│   │   ├── advisory.py
│   │   ├── crop_ml.py
│   │   └── disease.py
│   └── templates/
│       ├── base.html
│       ├── public_home.html
│       ├── dashboard.html
│       ├── auth/
│       └── services/
└── static/
    └── styles.css
```

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open `http://127.0.0.1:5000`.

## Deploy (Render)

This repo includes a basic [`render.yaml`](/Users/biyyani/AgroSmart/render.yaml) for a Flask + Gunicorn deploy.

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from the repo (it will read `render.yaml`).
3. Add environment variables in Render:
   - `DATABASE_URL`:
     - Recommended: use Render Postgres (managed).
     - If you insist on MySQL: you must run your own MySQL as a private service and set `DATABASE_URL` to `mysql://...` (the app auto-normalizes to `mysql+pymysql://`).
   - SMTP variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_TLS`, `SMTP_SSL`.

Note: For production, use a persistent disk or external storage for `uploads/` (otherwise uploaded images may not persist across deploys).

Recommended persistent paths (if you mount a Render Disk at `/var/data`):
- `UPLOAD_FOLDER=/var/data/uploads`
- `MODEL_STORE=/var/data/models`

## Email OTP Verification (Register/Login)

By default, members must verify an OTP sent to their email before logging in.

Set SMTP settings (example):

```bash
export REQUIRE_EMAIL_OTP=1
export EMAIL_DELIVERY=smtp
export SMTP_HOST="smtp.yourprovider.com"
export SMTP_PORT="587"
export SMTP_USER="your-agrosmart-email@domain.com"
export SMTP_PASS="your-smtp-password-or-app-password"
export SMTP_FROM="AgroSmart <your-agrosmart-email@domain.com>"
export SMTP_TLS=1
export SMTP_SSL=0
```

If you want to disable OTP locally:

```bash
export REQUIRE_EMAIL_OTP=0
```

## ML Training (Optional)

Crop model (RandomForest):

```bash
pip install -r requirements-ml.txt
python3 scripts/train_crop_model.py --data data/sample_crop_data.csv --out models/crop_model.joblib
```

Disease model (CNN/Keras, requires TensorFlow installed for your machine):

```bash
python3 scripts/train_disease_model.py --data_dir /path/to/leaf_dataset --out models/disease_model.keras
```

Once models exist, the web app auto-uses them; otherwise it falls back to safe placeholder logic.

## APIs

- `POST /api/crop/predict` (JSON)
- `POST /api/fertilizer/recommend` (JSON)
- `POST /api/disease/predict` (multipart: `leaf_image`)

All APIs require login (session cookie).

## Admin

Admin dashboard: `/admin/` (requires admin login).
Admin login page: `/admin/login`

Promote a user to admin:

```bash
python3 scripts/make_admin.py --email you@example.com
```

Admin login details:

- Use the same email/password as the promoted user.
- After login, admin session is stored separately as `admin_user_id`.

## Weather Auto-fill (OpenWeather)

Set an API key:

`export OPENWEATHER_API_KEY="your_key_here"`

Then on Crop Recommendation page, click "Auto-fill weather". It uses your Profile location by default.

## Languages + Voice Guidance

- Language selector is in the top bar (English/Hindi/Telugu).
- Each module page has Speak/Stop buttons (browser Text-to-Speech via Web Speech API).
