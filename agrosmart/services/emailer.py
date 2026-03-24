from __future__ import annotations

import re
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


_OTP_RE = re.compile(r"\b(\d{6})\b")

def _ssl_context() -> ssl.SSLContext:
    # On some macOS Python installs, the system CA bundle may not be available.
    # Prefer certifi when installed (recommended for reliable SMTP TLS).
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Best-effort email delivery.
    - console: store in app.extensions['sent_emails'] and print to server logs
    - smtp: send using SMTP_* settings
    """
    to_email = (to_email or "").strip().lower()
    if not to_email:
        return

    delivery = str(current_app.config.get("EMAIL_DELIVERY") or "console").lower()
    if current_app.config.get("TESTING") or delivery == "console":
        current_app.extensions.setdefault("sent_emails", []).append(
            {"to": to_email, "subject": subject, "body": body}
        )
        # Also emit to logs for local debugging.
        try:
            current_app.logger.info("Email(console) to=%s subject=%s body=%s", to_email, subject, body)
        except Exception:
            pass
        return

    host = str(current_app.config.get("SMTP_HOST") or "")
    port = int(current_app.config.get("SMTP_PORT") or 587)
    user = str(current_app.config.get("SMTP_USER") or "")
    password = str(current_app.config.get("SMTP_PASS") or "")
    from_addr = str(current_app.config.get("SMTP_FROM") or user or "no-reply@agrosmart.local")
    use_tls = bool(current_app.config.get("SMTP_TLS", True))
    use_ssl = bool(current_app.config.get("SMTP_SSL", False))

    if not host:
        # Misconfigured; do not crash the request.
        current_app.logger.warning("SMTP_HOST not set; skipping email delivery.")
        return

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if use_ssl:
            context = _ssl_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as s:
                if user and password:
                    s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                if use_tls:
                    s.starttls(context=_ssl_context())
                if user and password:
                    s.login(user, password)
                s.send_message(msg)
    except Exception:
        # Do not leak SMTP errors to the user; log for dev.
        current_app.logger.exception("Failed to send email via SMTP.")


def send_registration_otp(to_email: str, otp_code: str) -> None:
    subject = "AgroSmart OTP Verification"
    body = (
        "Your AgroSmart registration OTP is:\n\n"
        f"{otp_code}\n\n"
        "This OTP expires in a few minutes. If you did not request this, ignore this email."
    )
    send_email(to_email, subject, body)


def extract_otp_from_last_email() -> str | None:
    """
    Testing helper: returns 6-digit OTP from the last console email if present.
    """
    emails = current_app.extensions.get("sent_emails") or []
    if not emails:
        return None
    body = str(emails[-1].get("body") or "")
    m = _OTP_RE.search(body)
    return m.group(1) if m else None
