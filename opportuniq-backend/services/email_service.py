"""Reminder email delivery over SMTP.

Sends plain-text/HTML emails via STARTTLS SMTP (Gmail-compatible: an app
password, not the account password, goes in ``SMTP_APP_PASSWORD``).
``smtplib`` is blocking, so the actual send runs in a worker thread via
``asyncio.to_thread`` to keep the public function awaitable.

Scheduling *when* a reminder goes out is out of scope here — this module
only knows how to send one email on request.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SMTP_FROM_EMAIL_ENV = "SMTP_FROM_EMAIL"
SMTP_APP_PASSWORD_ENV = "SMTP_APP_PASSWORD"
SMTP_HOST_ENV = "SMTP_HOST"
SMTP_PORT_ENV = "SMTP_PORT"

# Gmail's STARTTLS submission endpoint; overridable via SMTP_HOST/SMTP_PORT
# for other providers without touching code.
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587

CONNECT_TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0  # doubles each retry: 2s, 4s, ...

# Failures worth retrying (transient network/server issues). Auth and
# recipient-address problems are not in this set — retrying them just
# wastes time and can trip provider rate limits.
_RETRYABLE_EXCEPTIONS = (
    smtplib.SMTPConnectError,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPHeloError,
    TimeoutError,
    OSError,
)


class EmailSendResult(BaseModel):
    """Outcome of a :func:`send_reminder_email` call."""

    success: bool = Field(description="True if the SMTP server accepted the message.")
    message_id: str | None = Field(default=None, description="Generated Message-ID when sent.")
    attempts: int = Field(description="Number of SMTP send attempts made.")
    error: str | None = Field(default=None, description="Human-readable failure reason, if any.")


class EmailConfigurationError(Exception):
    """Raised when required SMTP configuration is absent."""


async def send_reminder_email(
    to_email: str,
    subject: str,
    body: str,
    *,
    html_body: str | None = None,
) -> EmailSendResult:
    """Send a reminder email over SMTP with TLS, retrying transient failures.

    Args:
        to_email: Recipient address.
        subject: Email subject line.
        body: Plain-text message body.
        html_body: Optional HTML alternative rendered alongside ``body``.

    Returns:
        An :class:`EmailSendResult` describing success/failure — this
        function does not raise for delivery failures, only for
        programmer errors (blank recipient/subject/body or missing
        SMTP configuration).

    Raises:
        ValueError: ``to_email``, ``subject``, or ``body`` is blank.
        EmailConfigurationError: ``SMTP_FROM_EMAIL`` or ``SMTP_APP_PASSWORD``
            is not set.
    """
    if not to_email or not to_email.strip():
        raise ValueError("to_email must not be blank.")
    if not subject or not subject.strip():
        raise ValueError("subject must not be blank.")
    if not body or not body.strip():
        raise ValueError("body must not be blank.")

    from_email, app_password = _load_credentials()
    message = _build_message(from_email, to_email, subject, body, html_body)

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            await asyncio.to_thread(_send_sync, message, from_email, app_password)
            logger.info(
                "Sent reminder email to %s (attempt %d/%d, message-id=%s)",
                to_email,
                attempt,
                MAX_ATTEMPTS,
                message["Message-ID"],
            )
            return EmailSendResult(success=True, message_id=message["Message-ID"], attempts=attempt)

        except smtplib.SMTPAuthenticationError as exc:
            # Bad credentials will never succeed on retry — fail fast.
            logger.error("SMTP authentication failed for %s: %s", from_email, exc)
            return EmailSendResult(
                success=False,
                attempts=attempt,
                error=f"SMTP authentication failed: {exc}",
            )

        except smtplib.SMTPRecipientsRefused as exc:
            # A bad recipient address is not fixed by retrying either.
            logger.error("SMTP server refused recipient %s: %s", to_email, exc)
            return EmailSendResult(
                success=False,
                attempts=attempt,
                error=f"Recipient refused: {exc}",
            )

        except _RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            logger.warning(
                "SMTP send attempt %d/%d to %s failed: %s",
                attempt,
                MAX_ATTEMPTS,
                to_email,
                exc,
            )
            if attempt < MAX_ATTEMPTS:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))

        except smtplib.SMTPException as exc:
            # Any other SMTP-level failure: treat as non-retryable.
            logger.exception("SMTP send to %s failed", to_email)
            return EmailSendResult(success=False, attempts=attempt, error=str(exc))

    logger.error(
        "Giving up sending to %s after %d attempts: %s", to_email, MAX_ATTEMPTS, last_error
    )
    return EmailSendResult(
        success=False,
        attempts=MAX_ATTEMPTS,
        error=f"Failed after {MAX_ATTEMPTS} attempts: {last_error}",
    )


def _load_credentials() -> tuple[str, str]:
    """Read and validate SMTP credentials from the environment.

    Raises:
        EmailConfigurationError: Either variable is unset/blank.
    """
    from_email = os.getenv(SMTP_FROM_EMAIL_ENV, "").strip()
    app_password = os.getenv(SMTP_APP_PASSWORD_ENV, "").strip()

    if not from_email:
        raise EmailConfigurationError(f"{SMTP_FROM_EMAIL_ENV} environment variable is not set.")
    if not app_password:
        raise EmailConfigurationError(f"{SMTP_APP_PASSWORD_ENV} environment variable is not set.")

    return from_email, app_password


def _build_message(
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None,
) -> EmailMessage:
    """Assemble a plain-text (+ optional HTML alternative) email message."""
    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message["Message-ID"] = make_msgid()
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def _send_sync(message: EmailMessage, from_email: str, app_password: str) -> None:
    """Blocking STARTTLS send; runs off the event loop via ``asyncio.to_thread``.

    Raises:
        smtplib.SMTPException: On any SMTP-level failure (auth, refused
            recipients, protocol errors, etc.).
        OSError: On connection/socket failures (including timeouts).
    """
    host = os.getenv(SMTP_HOST_ENV, "").strip() or DEFAULT_SMTP_HOST
    port = int(os.getenv(SMTP_PORT_ENV, "").strip() or DEFAULT_SMTP_PORT)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=CONNECT_TIMEOUT_SECONDS) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(from_email, app_password)
        server.send_message(message)
