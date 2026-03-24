from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test email using AgroSmart SMTP settings.")
    parser.add_argument("--to", required=True, help="Recipient email")
    args = parser.parse_args()

    # Allow running without installing the package.
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from agrosmart import create_app
    from agrosmart.services.emailer import send_email

    app = create_app()
    with app.app_context():
        send_email(
            args.to,
            "AgroSmart SMTP Test",
            "This is a test email from AgroSmart. If you received this, SMTP is configured correctly.",
        )
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

