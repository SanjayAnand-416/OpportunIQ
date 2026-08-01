"""Canonical asynchronous SMTP reminder adapter."""

import asyncio
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from app.config import SMTP_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, body: str) -> None:
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    password = os.getenv("SMTP_APP_PASSWORD", "").strip()
    if not sender or not password: raise RuntimeError("SMTP is not configured")
    message = EmailMessage(); message["From"] = sender; message["To"] = to_email; message["Subject"] = subject; message.set_content(body)
    host = os.getenv("SMTP_HOST", "smtp.gmail.com"); port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS) as server:
        server.starttls(context=ssl.create_default_context()); server.login(sender, password); server.send_message(message)


async def send_reminder_email(*, to_email: str, subject: str, body: str) -> bool:
    if not to_email.strip(): return False
    try:
        await asyncio.wait_for(
            asyncio.to_thread(_send, to_email.strip(), subject, body),
            timeout=SMTP_TIMEOUT_SECONDS,
        )
        return True
    except Exception as exc:
        logger.warning("Reminder email delivery failed: %s", type(exc).__name__)
        return False
