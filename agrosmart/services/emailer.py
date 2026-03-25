from __future__ import annotations

import re
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


_OTP_RE = re.compile(r"\b(\d{6})\b")


def _send_email_resend(to_email: str, subject: str, body: str) -> bool:
    api_key = str(current_app.config.get("RESEND_API_KEY") or "").strip()
    from_addr = str(current_app.config.get("RESEND_FROM") or "").strip()
    if not api_key or not from_addr:
        current_app.logger.warning("Resend not configured (RESEND_API_KEY/RESEND_FROM missing).")
        return False

    try:
        import requests  # type: ignore

        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_addr, "to": [to_email], "subject": subject, "text": body},
            timeout=20,
        )
        if 200 <= resp.status_code < 300:
            return True
        current_app.logger.error("Resend email failed status=%s body=%s", resp.status_code, resp.text[:400])
        return False
    except Exception:
        current_app.logger.exception("Failed to send email via Resend.")
        return False


def _ssl_context() -> ssl.SSLContext:
    # On some macOS Python installs, the system CA bundle may not be available.
    # Prefer certifi when installed (recommended for reliable SMTP TLS).
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Best-effort email delivery.
    - console: store in app.extensions['sent_emails'] and print to server logs
    - smtp: send using SMTP_* settings
    - resend: send using Resend HTTPS API (recommended on Render where SMTP is blocked)
    """
    to_email = (to_email or "").strip().lower()
    if not to_email:
        return False

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
        return True

    if delivery == "resend":
        return _send_email_resend(to_email=to_email, subject=subject, body=body)

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
        return False

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
        return False

    return True


def send_registration_otp(to_email: str, otp_code: str) -> bool:
    subject = "AgroSmart OTP Verification"
    body = (
        "Your AgroSmart registration OTP is:\n\n"
        f"{otp_code}\n\n"
        "This OTP expires in a few minutes. If you did not request this, ignore this email."
    )
    return send_email(to_email, subject, body)


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
