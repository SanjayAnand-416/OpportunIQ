"""Opportunity deduplication and relevance ranking.

Three responsibilities live here:

1. ``normalise_url``   - canonicalise a URL so the same posting mirrored on
                          two sites hashes identically.
2. ``deduplicate``     - collapse duplicate postings using URL hashing
                          (layer 1) and fuzzy title matching (layer 2),
                          merging duplicate sources into ``also_on``
                          (layer 3).
3. ``score``            - rank one opportunity against a student profile
                          using semantic skill similarity + deadline
                          urgency.

Kept dependency-light and synchronous: SentenceTransformer/RapidFuzz have no
async APIs, so nothing here is a coroutine.
"""

from __future__ import annotations

import logging
from datetime import date
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util

from models import StudentProfile
from services.groq_service import Opportunity

logger = logging.getLogger(__name__)

# Sentence-transformer model used for skill-similarity embeddings.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Layer-2 threshold: RapidFuzz token_sort_ratio (0-100) above which two
# titles are considered the same opportunity.
TITLE_SIMILARITY_THRESHOLD = 90.0

# Deadlines this many days out (or further) contribute no urgency; anything
# closer ramps linearly up to 1.0 at the deadline itself.
URGENCY_HORIZON_DAYS = 30

# Final score weights: 0.7 * skill_score + 0.3 * urgency.
SKILL_SCORE_WEIGHT = 0.7
URGENCY_WEIGHT = 0.3

# Tracking/session query params that don't change what page loads; stripped
# during URL normalisation so mirrored links still hash the same.
_IGNORED_QUERY_PREFIXES = ("utm_", "ref", "src", "gclid", "fbclid", "session")

_embedding_model: SentenceTransformer | None = None


class OpportunityListing(BaseModel):
    """One opportunity posting as scraped/ingested from a single source."""

    opportunity: Opportunity = Field(description="Structured opportunity data.")
    url: str = Field(description="Original posting URL, any casing/format.")
    source: str | None = Field(default=None, description="Site or feed name, e.g. 'LinkedIn'.")


class DeduplicatedListing(BaseModel):
    """A canonical listing with duplicate postings merged into ``also_on``."""

    opportunity: Opportunity = Field(
        description="Structured opportunity data of the canonical posting."
    )
    url: str = Field(description="Canonical (first-seen) posting URL.")
    source: str | None = Field(default=None, description="Source of the canonical posting.")
    also_on: list[str] = Field(
        default_factory=list,
        description="Sources/URLs of other postings merged into this one.",
    )


class ScoredOpportunity(BaseModel):
    """A deduplicated listing with its computed relevance score."""

    listing: DeduplicatedListing = Field(description="The scored listing.")
    skill_score: float = Field(
        ge=0.0, le=1.0, description="Cosine similarity of required vs. student skills."
    )
    urgency_score: float = Field(
        ge=0.0, le=1.0, description="1.0 = deadline is now, 0.0 = far away/none."
    )
    final_score: float = Field(
        ge=0.0, le=1.0, description="0.7 * skill_score + 0.3 * urgency_score."
    )


def normalise_url(url: str) -> str:
    """Canonicalise a URL so mirrored/tracked links compare equal.

    Normalisation applied:
        - scheme and host lowercased, default ``www.`` prefix dropped
        - trailing slash on the path removed
        - fragment (``#...``) dropped
        - tracking query params (utm_*, ref, src, gclid, fbclid, session*)
          removed; remaining params sorted for stable ordering

    Args:
        url: A raw URL, possibly missing a scheme (e.g. "example.com/x").

    Returns:
        The canonical form of ``url``, or ``""`` if ``url`` is blank.
    """
    raw = (url or "").strip()
    if not raw:
        return ""

    # Bare domains ("example.com/job") have no scheme; urlsplit would treat
    # the whole string as a path, so add a scheme before parsing.
    if "//" not in raw:
        raw = f"//{raw}"

    parts = urlsplit(raw, scheme="https")
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    path = parts.path.rstrip("/") or "/"

    kept_params = [
        param
        for param in parts.query.split("&")
        if param and not param.split("=", 1)[0].lower().startswith(_IGNORED_QUERY_PREFIXES)
    ]
    query = "&".join(sorted(kept_params))

    # Scheme (http vs https) never changes the identity of a posting.
    return urlunsplit(("https", host, path, query, ""))


def deduplicate(
    listings: list[OpportunityListing],
    *,
    title_similarity_threshold: float = TITLE_SIMILARITY_THRESHOLD,
) -> list[DeduplicatedListing]:
    """Collapse duplicate opportunity postings from multiple sources.

    Layer 1 groups postings whose normalised URLs are identical. Layer 2
    then fuzzy-matches titles (RapidFuzz ``token_sort_ratio``, organisation
    equal when both are known) across the remaining groups to catch the
    same posting reachable via different URLs. Layer 3 merges every
    duplicate's source/URL into the canonical listing's ``also_on``.

    Args:
        listings: Raw postings, typically gathered from several sources.
        title_similarity_threshold: Minimum RapidFuzz score (0-100) for two
            titles to be treated as the same opportunity.

    Returns:
        One :class:`DeduplicatedListing` per distinct opportunity, in
        first-seen order.
    """
    # --- Layer 1: exact match on normalised URL -----------------------
    url_groups: dict[str, list[OpportunityListing]] = {}
    order: list[str] = []
    for listing in listings:
        key = normalise_url(listing.url)
        if key not in url_groups:
            url_groups[key] = []
            order.append(key)
        url_groups[key].append(listing)

    canonical: list[DeduplicatedListing] = [
        DeduplicatedListing(
            opportunity=url_groups[key][0].opportunity,
            url=url_groups[key][0].url,
            source=url_groups[key][0].source,
            also_on=_sources_of(url_groups[key][1:]),
        )
        for key in order
    ]

    # --- Layer 2: fuzzy title match across the remaining groups --------
    merged: list[DeduplicatedListing] = []
    for candidate in canonical:
        match = _find_title_match(candidate, merged, title_similarity_threshold)
        if match is None:
            merged.append(candidate)
            continue

        # Layer 3: fold the duplicate's own source and also_on entries in.
        match.also_on.extend(_sources_of([candidate]))
        match.also_on.extend(candidate.also_on)
        logger.debug(
            "Merged duplicate opportunity '%s' into '%s'",
            candidate.opportunity.title,
            match.opportunity.title,
        )

    logger.info("Deduplicated %d listing(s) into %d opportunity/ies", len(listings), len(merged))
    return merged


def score(
    profile: StudentProfile,
    opportunity: DeduplicatedListing | OpportunityListing | Opportunity,
    *,
    reference_date: date | None = None,
) -> ScoredOpportunity:
    """Score one opportunity's relevance to a student.

    ``final_score = 0.7 * skill_score + 0.3 * urgency_score``, where
    ``skill_score`` is the cosine similarity between sentence-transformer
    embeddings of the student's skills and the opportunity's required
    skills, and ``urgency_score`` rises linearly to 1.0 as the deadline
    approaches (0.0 once it has passed or is 30+ days out).

    Args:
        profile: The student being matched.
        opportunity: The opportunity to score, in any of the three shapes
            produced by this module (a bare :class:`Opportunity`, an
            un-deduplicated :class:`OpportunityListing`, or a
            :class:`DeduplicatedListing`).
        reference_date: "Today" for urgency math; defaults to the current
            local date.

    Returns:
        A :class:`ScoredOpportunity` wrapping the listing and its scores.
    """
    listing = _as_deduplicated_listing(opportunity)

    skill_score = _skill_similarity(profile.skills, listing.opportunity.skills_required)
    urgency_score = _urgency(listing.opportunity.deadline, reference_date or date.today())
    final_score = SKILL_SCORE_WEIGHT * skill_score + URGENCY_WEIGHT * urgency_score

    return ScoredOpportunity(
        listing=listing,
        skill_score=skill_score,
        urgency_score=urgency_score,
        final_score=final_score,
    )


def get_embedding_model() -> SentenceTransformer:
    """Return the lazily loaded, process-wide SentenceTransformer model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading SentenceTransformer model '%s'", EMBEDDING_MODEL_NAME)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def _skill_similarity(student_skills: list[str], required_skills: list[str]) -> float:
    """Cosine-similarity of two skill lists via sentence embeddings.

    Each skill list is joined into one sentence so the embedding captures
    the whole skill set rather than averaging per-skill vectors.

    Returns:
        A value in ``[0.0, 1.0]``; ``0.0`` if either list is empty.
    """
    if not student_skills or not required_skills:
        return 0.0

    student_text = ", ".join(student_skills)
    required_text = ", ".join(required_skills)

    model = get_embedding_model()
    embeddings = model.encode([student_text, required_text], convert_to_tensor=True)
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()

    # Cosine similarity can dip slightly negative for unrelated embeddings;
    # clamp to a proper [0, 1] score.
    return max(0.0, min(1.0, similarity))


def _urgency(deadline: date | None, today: date) -> float:
    """Linear urgency ramp: 1.0 at the deadline, 0.0 at/after the horizon.

    Returns:
        ``0.0`` when there is no deadline, it has already passed, or it is
        ``URGENCY_HORIZON_DAYS`` or more days away; otherwise a value in
        ``(0.0, 1.0]``.
    """
    if deadline is None:
        return 0.0

    days_remaining = (deadline - today).days
    if days_remaining < 0 or days_remaining >= URGENCY_HORIZON_DAYS:
        return 0.0

    return 1.0 - (days_remaining / URGENCY_HORIZON_DAYS)


def _find_title_match(
    candidate: DeduplicatedListing,
    against: list[DeduplicatedListing],
    threshold: float,
) -> DeduplicatedListing | None:
    """Return the first listing in ``against`` that is a fuzzy title match.

    Two listings match when their titles score at or above ``threshold`` on
    RapidFuzz's ``token_sort_ratio`` (order-independent word overlap) and,
    whenever both organisations are known, the organisations also match —
    this stops "Software Engineer Intern" at two different companies from
    being merged.
    """
    for existing in against:
        similarity = fuzz.token_sort_ratio(
            candidate.opportunity.title.lower(),
            existing.opportunity.title.lower(),
        )
        if similarity < threshold:
            continue

        cand_org = (candidate.opportunity.organization or "").strip().lower()
        exist_org = (existing.opportunity.organization or "").strip().lower()
        if cand_org and exist_org and cand_org != exist_org:
            continue

        return existing
    return None


def _sources_of(listings: list[OpportunityListing]) -> list[str]:
    """Extract a display label (source name, falling back to URL) per listing."""
    return [listing.source or listing.url for listing in listings]


def _as_deduplicated_listing(
    opportunity: DeduplicatedListing | OpportunityListing | Opportunity,
) -> DeduplicatedListing:
    """Normalise any of the three accepted shapes into a DeduplicatedListing."""
    if isinstance(opportunity, DeduplicatedListing):
        return opportunity
    if isinstance(opportunity, OpportunityListing):
        return DeduplicatedListing(
            opportunity=opportunity.opportunity, url=opportunity.url, source=opportunity.source
        )
    return DeduplicatedListing(
        opportunity=opportunity, url=opportunity.application_url or "", source=None
    )
