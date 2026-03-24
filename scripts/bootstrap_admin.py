from __future__ import annotations

import argparse
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

# Allow running without installing the package.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agrosmart import create_app
from agrosmart.db import db
from agrosmart.models import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update an admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="AgroSmart Admin")
    args = parser.parse_args()

    email = args.email.strip().lower()
    password = args.password
    name = args.name.strip() or "AgroSmart Admin"

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(name=name, email=email, password_hash=generate_password_hash(password), is_admin=True)
            db.session.add(user)
        else:
            user.name = name
            user.password_hash = generate_password_hash(password)
            user.is_admin = True
        # Admin accounts should be treated as verified for local demos.
        if hasattr(user, "email_verified"):
            user.email_verified = True
            if hasattr(user, "email_verified_at") and user.email_verified_at is None:
                from agrosmart.db import utcnow

                user.email_verified_at = utcnow()
        db.session.commit()
        print(f"Admin ready: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
