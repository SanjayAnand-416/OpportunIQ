"""Small runtime configuration helpers for the active backend package."""

import logging
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


logger = logging.getLogger(__name__)

DEFAULT_APP_TIMEZONE = "Asia/Kolkata"


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
