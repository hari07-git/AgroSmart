from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # In production, set SECRET_KEY via environment (Render/host dashboard).
    SECRET_KEY = os.getenv("SECRET_KEY", "agrosmart-dev-key-change-me")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    # Allow overriding upload path for production persistent disks.
    UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads")))
    # Database:
    # - Local default: SQLite
    # - Production: set DATABASE_URL (Render/Railway provide this)
    _default_db = f"sqlite:///{(BASE_DIR / 'agrosmart.sqlite3')}"
    _db = os.getenv("DATABASE_URL", _default_db).strip()
    # Normalize common provider URLs.
    if _db.startswith("postgres://"):
        # Use SQLAlchemy default driver (psycopg2-binary) for best deploy compatibility.
        _db = _db.replace("postgres://", "postgresql://", 1)
    if _db.startswith("mysql://"):
        _db = _db.replace("mysql://", "mysql+pymysql://", 1)
    SQLALCHEMY_DATABASE_URI = _db
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CROP_MODEL_PATH = BASE_DIR / "models" / "crop_model.joblib"
    DISEASE_MODEL_PATH = BASE_DIR / "models" / "disease_model.keras"
    MODEL_STORE = Path(os.getenv("MODEL_STORE", str(BASE_DIR / "models")))

    # Email (OTP verification)
    # Email delivery:
    # - console: store in server logs (dev)
    # - smtp: traditional SMTP (often blocked on PaaS)
    # - resend: HTTPS email API (recommended for Render)
    EMAIL_DELIVERY = os.getenv("EMAIL_DELIVERY", "console")  # console | smtp | resend
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@agrosmart.local")
    SMTP_TLS = os.getenv("SMTP_TLS", "1") not in ("0", "false", "False")
    SMTP_SSL = os.getenv("SMTP_SSL", "0") in ("1", "true", "True")

    # Resend (HTTPS email API)
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM = os.getenv("RESEND_FROM", SMTP_FROM)

    OTP_EXPIRES_MINUTES = int(os.getenv("OTP_EXPIRES_MINUTES", "10"))
    OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
    OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    # Enable OTP by default for real deployments; tests override this to False.
    REQUIRE_EMAIL_OTP = os.getenv("REQUIRE_EMAIL_OTP", "1") in ("1", "true", "True")
    # Demo-only: if email delivery fails, optionally show OTP on the verify screen.
    # Keep this OFF for real deployments.
    OTP_DEBUG_SHOW = os.getenv("OTP_DEBUG_SHOW", "0") in ("1", "true", "True")

    # Admin bootstrap (demo convenience)
    # For real production, set BOOTSTRAP_ADMIN=0 and manage admins manually.
    BOOTSTRAP_ADMIN = os.getenv("BOOTSTRAP_ADMIN", "1") in ("1", "true", "True")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@agrosmart.com").strip().lower()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin@1234")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "AgroSmart Admin")
