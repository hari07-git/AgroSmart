from __future__ import annotations

import argparse

from agrosmart import create_app
from agrosmart.db import db
from agrosmart.models import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a user to admin by email.")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=args.email.strip().lower()).first()
        if not user:
            raise SystemExit("User not found.")
        user.is_admin = True
        db.session.commit()
        print(f"User promoted to admin: {user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
