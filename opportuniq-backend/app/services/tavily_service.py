"""Tavily discovery service used by the active opportunity router."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from tavily import TavilyClient


logger = logging.getLogger(__name__)

SEARCH_DEPTH = "basic"
RESULTS_PER_QUERY = 5

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

    queries = [
        f"{role} hackathon 2025 site:unstop.com",
        "machine learning hackathon site:devfolio.co",
        f"{role} internship site:hackerearth.com",
        f"{' '.join(skills[:3])} internship site:internshala.com",
        f"{role} fresher jobs company careers portal {search_location} 2025",
    ]

    results: list[dict[str, Any]] = []
    for query in queries:
        try:
            response = await asyncio.to_thread(
                client.search,
                query,
                search_depth=SEARCH_DEPTH,
                max_results=RESULTS_PER_QUERY,
            )
            query_results = response.get("results", [])
            if isinstance(query_results, list):
                results.extend(item for item in query_results if isinstance(item, dict))
        except Exception as exc:
            logger.warning("Tavily error for query %r: %s", query, exc)

    return results[:safe_limit]
