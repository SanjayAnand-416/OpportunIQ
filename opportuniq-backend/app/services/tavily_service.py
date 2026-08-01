"""Tavily discovery service used by the active opportunity router."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from requests import RequestException
from requests import Timeout as RequestsTimeout
from tavily import (
    InvalidAPIKeyError,
    KeylessUnsupportedEndpointError,
    MissingAPIKeyError,
    TavilyClient,
    TavilyKeylessLimitError,
    UsageLimitExceededError,
)

from app.config import EXTERNAL_HTTP_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)

SEARCH_DEPTH = "basic"
RESULTS_PER_QUERY = 5


class TavilyIntegrationError(RuntimeError):
    """Base error carrying a safe provider-failure category."""

    code = "provider_error"


class TavilyCredentialError(TavilyIntegrationError):
    """Raised when Tavily credentials or account quota reject every query."""

    code = "credential_failure"


class TavilyTimeoutError(TavilyIntegrationError):
    """Raised when every usable Tavily result is lost to request timeouts."""

    code = "timeout"


class TavilyNetworkError(TavilyIntegrationError):
    """Raised when Tavily cannot be reached and no result survives."""

    code = "network_failure"

# Preserve Person C's environment-based client configuration. Keeping the
# client injectable at module scope also makes the provider boundary testable.
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


async def search_hackathons_and_portals(
    role: str,
    skills: list[str],
    location: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search Person C's targeted hackathon, internship, and portal queries."""
    search_location = (location or "India").strip() or "India"
    safe_limit = max(0, int(limit))
    if safe_limit == 0:
        return []

    current_year = datetime.now(UTC).year
    queries = [
        f"{role} hackathon {current_year} site:unstop.com",
        "machine learning hackathon site:devfolio.co",
        f"{role} internship site:hackerearth.com",
        f"{' '.join(skills[:3])} internship site:internshala.com",
        f"{role} fresher jobs company careers portal {search_location} {current_year}",
    ]

    results: list[dict[str, Any]] = []
    failures: list[TavilyIntegrationError] = []
    for query in queries:
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.search,
                    query,
                    search_depth=SEARCH_DEPTH,
                    max_results=RESULTS_PER_QUERY,
                    timeout=EXTERNAL_HTTP_TIMEOUT_SECONDS,
                ),
                timeout=EXTERNAL_HTTP_TIMEOUT_SECONDS,
            )
            query_results = response.get("results", [])
            if isinstance(query_results, list):
                results.extend(item for item in query_results if isinstance(item, dict))
        except (
            InvalidAPIKeyError,
            MissingAPIKeyError,
            KeylessUnsupportedEndpointError,
            TavilyKeylessLimitError,
            UsageLimitExceededError,
        ) as exc:
            logger.warning("Tavily rejected configured credentials or account access")
            raise TavilyCredentialError("Tavily credentials or account access were rejected") from exc
        except (asyncio.TimeoutError, TimeoutError, RequestsTimeout) as exc:
            logger.warning("Tavily request timed out for query %r", query)
            failures.append(TavilyTimeoutError("Tavily request timed out"))
        except RequestException as exc:
            logger.warning("Tavily network request failed for query %r", query)
            failures.append(TavilyNetworkError("Tavily network request failed"))
        except Exception as exc:
            logger.warning("Tavily provider error for query %r: %s", query, type(exc).__name__)
            failures.append(TavilyIntegrationError("Tavily provider request failed"))

    if results:
        return results[:safe_limit]
    if failures:
        if any(isinstance(failure, TavilyTimeoutError) for failure in failures):
            raise TavilyTimeoutError("Tavily requests timed out")
        if any(isinstance(failure, TavilyNetworkError) for failure in failures):
            raise TavilyNetworkError("Tavily network requests failed")
        raise failures[0]
    return []
