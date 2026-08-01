"""Small runtime configuration helpers for the active backend package."""

import logging
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


logger = logging.getLogger(__name__)

DEFAULT_APP_TIMEZONE = "Asia/Kolkata"


def _positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError:
        logger.warning("Invalid %s value; using %.1f seconds", name, default)
        return default
    if value <= 0:
        logger.warning("Non-positive %s value; using %.1f seconds", name, default)
        return default
    return value


def _boolean(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_app_timezone() -> ZoneInfo:
    """Return the configured application timezone with a safe fallback."""
    timezone_name = os.getenv("APP_TIMEZONE", DEFAULT_APP_TIMEZONE).strip()
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(
            "Invalid APP_TIMEZONE %r; falling back to %s",
            timezone_name,
            DEFAULT_APP_TIMEZONE,
        )
        return ZoneInfo(DEFAULT_APP_TIMEZONE)


APP_TIMEZONE = get_app_timezone()
EXTERNAL_HTTP_TIMEOUT_SECONDS = _positive_float(
    "EXTERNAL_HTTP_TIMEOUT_SECONDS", 30.0
)
AGENT_TIMEOUT_SECONDS = _positive_float("AGENT_TIMEOUT_SECONDS", 60.0)
SMTP_TIMEOUT_SECONDS = _positive_float("SMTP_TIMEOUT_SECONDS", 20.0)
JOBSPY_TIMEOUT_SECONDS = _positive_float("JOBSPY_TIMEOUT_SECONDS", 30.0)
ENABLE_SCHEDULER = _boolean("ENABLE_SCHEDULER", True)
DEMO_MODE = _boolean("DEMO_MODE", False)
