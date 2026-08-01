"""LLM extraction and generation backed by Groq + instructor.

Every public function is async and returns a validated Pydantic model — never
free-form text. The Groq client is created lazily and reused across calls.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from enum import Enum
from typing import Any, TypeVar

import groq
import instructor
from instructor.core.exceptions import InstructorRetryException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

GROQ_API_KEY_ENV = "GROQ_API_KEY"
GROQ_MODEL_ENV = "GROQ_MODEL"
GROQ_TIMEOUT_ENV = "GROQ_TIMEOUT_SECONDS"
GROQ_MAX_RETRIES_ENV = "GROQ_MAX_RETRIES"

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_TEMPERATURE = 0.0
GAP_ANALYSIS_MODEL = "openai/gpt-oss-120b"

# Guard against pathological inputs blowing the context window / token budget.
MAX_INPUT_CHARS = 24_000

T = TypeVar("T", bound=BaseModel)

_client: instructor.AsyncInstructor | None = None


class GroqServiceError(Exception):
    """Base error for every failure raised by this service."""


class GroqConfigurationError(GroqServiceError):
    """Raised when required Groq configuration is absent or invalid."""


class GroqInputError(GroqServiceError):
    """Raised when the caller supplies unusable input text."""


class GroqTimeoutError(GroqServiceError):
    """Raised when Groq does not respond within the timeout window."""


class GroqRateLimitError(GroqServiceError):
    """Raised when Groq rejects the call for rate limiting / quota reasons."""


class GroqExtractionError(GroqServiceError):
    """Raised when Groq fails to return a valid structured response."""


class OpportunityType(str, Enum):
    """Kind of opportunity described by a posting."""

    INTERNSHIP = "internship"
    JOB = "job"
    SCHOLARSHIP = "scholarship"
    HACKATHON = "hackathon"
    COMPETITION = "competition"
    COURSE = "course"
    FELLOWSHIP = "fellowship"
    CONFERENCE = "conference"
    OTHER = "other"


class WorkMode(str, Enum):
    """Where the opportunity is carried out."""

    REMOTE = "remote"
    ONSITE = "onsite"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class Urgency(str, Enum):
    """How pressing a reminder is, derived from days remaining."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Opportunity(BaseModel):
    """A structured opportunity extracted from unstructured text."""

    title: str = Field(description="Role or programme name, e.g. 'SDE Intern 2026'.")
    organization: str | None = Field(
        default=None, description="Company, university, or body offering it."
    )
    opportunity_type: OpportunityType = Field(
        default=OpportunityType.OTHER, description="Best-fit category."
    )
    summary: str | None = Field(default=None, description="Two-sentence plain-English summary.")
    location: str | None = Field(default=None, description="City/country, null if unstated.")
    work_mode: WorkMode = Field(default=WorkMode.UNKNOWN, description="Remote/onsite/hybrid.")
    eligibility: list[str] = Field(
        default_factory=list, description="Eligibility criteria, one per item."
    )
    skills_required: list[str] = Field(
        default_factory=list, description="Named skills/technologies only."
    )
    stipend: str | None = Field(default=None, description="Compensation exactly as stated.")
    application_url: str | None = Field(default=None, description="Direct application link.")
    deadline: date | None = Field(default=None, description="Application deadline (ISO date).")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence this is a real opportunity."
    )

    @field_validator(
        "organization", "summary", "location", "stipend", "application_url", mode="before"
    )
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        """Treat blank/placeholder strings from the model as ``None``."""
        return _clean_optional_str(value)

    @field_validator("deadline", mode="before")
    @classmethod
    def _empty_date_to_none(cls, value: Any) -> Any:
        """Tolerate ``""``/``"null"``/``"N/A"`` where a date was requested."""
        return _clean_optional_str(value)


class DeadlineExtraction(BaseModel):
    """The deadline (if any) stated in an email or notice."""

    has_deadline: bool = Field(description="True only if a concrete deadline is stated.")
    deadline_date: date | None = Field(default=None, description="Resolved deadline (ISO date).")
    deadline_time: str | None = Field(default=None, description="24h local time, e.g. '23:59'.")
    timezone: str | None = Field(default=None, description="Timezone if stated, e.g. 'IST'.")
    raw_deadline_text: str | None = Field(
        default=None, description="Verbatim snippet the deadline came from."
    )
    is_relative: bool = Field(
        default=False, description="True if stated relatively, e.g. 'within 7 days'."
    )
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Extraction confidence.")

    @field_validator("deadline_time", "timezone", "raw_deadline_text", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        """Treat blank/placeholder strings from the model as ``None``."""
        return _clean_optional_str(value)

    @field_validator("deadline_date", mode="before")
    @classmethod
    def _empty_date_to_none(cls, value: Any) -> Any:
        """Tolerate ``""``/``"null"``/``"N/A"`` where a date was requested."""
        return _clean_optional_str(value)


class ReminderMessage(BaseModel):
    """A ready-to-send reminder about an approaching deadline."""

    subject: str = Field(description="Email subject line, max ~70 characters.")
    body: str = Field(description="Reminder body, 3-6 short sentences, no placeholders.")
    call_to_action: str = Field(description="One imperative next step.")
    urgency: Urgency = Field(default=Urgency.MEDIUM, description="Urgency conveyed by the tone.")


class JDSkillsExtraction(BaseModel):
    """Skill categories extracted from a pasted job description."""

    required_skills: list[str] = Field(
        default_factory=list,
        description="Skills explicitly required by the job description.",
    )
    preferred_skills: list[str] = Field(
        default_factory=list,
        description="Skills described as preferred, desirable, or nice to have.",
    )
    tech_stack: list[str] = Field(
        default_factory=list,
        description="Named languages, frameworks, tools, platforms, and databases.",
    )

    @field_validator("required_skills", "preferred_skills", "tech_stack")
    @classmethod
    def _normalize_skills(cls, values: list[str]) -> list[str]:
        """Remove blank and duplicate model outputs while preserving order."""
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            skill = value.strip()
            key = skill.lower()
            if skill and key not in seen:
                normalized.append(skill)
                seen.add(key)
        return normalized


class GapLearningResource(BaseModel):
    """A concrete learning resource recommended for one deterministic gap."""

    resource: str = Field(min_length=1, description="Name of the learning resource.")
    url: str = Field(min_length=4, description="Real resource URL beginning with http.")

    @field_validator("resource", "url", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("url")
    @classmethod
    def _require_http_url(cls, value: str) -> str:
        if not value.startswith("http"):
            raise ValueError("Learning resource URL must begin with http.")
        return value


class GapMissingSkill(BaseModel):
    """LLM narrative attached to a deterministically identified gap."""

    skill: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    learning_resources: list[GapLearningResource] = Field(min_length=1, max_length=5)

    @field_validator("skill", "reason", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()


class GapSuggestedProject(BaseModel):
    """A practical project that addresses deterministic skill gaps."""

    project_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    skills_addressed: list[str] = Field(min_length=1)

    @field_validator("project_type", "description", mode="before")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()


class GapAnalysisLLMOutput(BaseModel):
    """Validated narrative synthesis returned by the gap-analysis LLM."""

    overall_assessment: str = Field(
        min_length=20,
        description="Two-to-three sentence assessment of readiness for the target role.",
    )
    missing_skills: list[GapMissingSkill] = Field(max_length=8)
    suggested_projects: list[GapSuggestedProject] = Field(min_length=3, max_length=3)

    @field_validator("overall_assessment", mode="before")
    @classmethod
    def _strip_assessment(cls, value: str) -> str:
        return value.strip()


async def extract_opportunity(
    raw_text: str,
    *,
    reference_date: date | None = None,
) -> Opportunity:
    """Extract a structured :class:`Opportunity` from unstructured text.

    Args:
        raw_text: Job post, email, or scraped page describing an opportunity.
        reference_date: "Today" used to resolve relative dates; defaults to
            the current local date.

    Returns:
        The extracted :class:`Opportunity`.

    Raises:
        GroqInputError: ``raw_text`` is blank.
        GroqConfigurationError: ``GROQ_API_KEY`` is missing.
        GroqTimeoutError: Groq did not respond in time.
        GroqRateLimitError: Groq rate limited the request.
        GroqExtractionError: Groq returned no valid structured response.
    """
    text = _require_text(raw_text, "raw_text")
    today = reference_date or date.today()

    system = (
        "You extract structured opportunity data for a student career platform. "
        "Use ONLY facts present in the text — never invent an organization, URL, "
        "stipend, or deadline. Use null for anything not stated. "
        f"Today is {today.isoformat()}; resolve relative dates against it and "
        "return every date as ISO YYYY-MM-DD. "
        "Set confidence below 0.4 if the text is not actually an opportunity."
    )

    logger.info("Extracting opportunity from %d chars of text", len(text))
    return await _complete(
        response_model=Opportunity,
        system_prompt=system,
        user_prompt=f"Opportunity text:\n\n{text}",
        operation="extract_opportunity",
    )


async def extract_deadline(
    email_text: str,
    *,
    reference_date: date | None = None,
) -> DeadlineExtraction:
    """Extract the application/submission deadline from an email or notice.

    Args:
        email_text: Raw email body or notice text.
        reference_date: "Today" used to resolve relative deadlines such as
            "within 7 days"; defaults to the current local date.

    Returns:
        A :class:`DeadlineExtraction`; ``has_deadline`` is ``False`` when the
        text states no deadline.

    Raises:
        GroqInputError: ``email_text`` is blank.
        GroqConfigurationError: ``GROQ_API_KEY`` is missing.
        GroqTimeoutError: Groq did not respond in time.
        GroqRateLimitError: Groq rate limited the request.
        GroqExtractionError: Groq returned no valid structured response.
    """
    text = _require_text(email_text, "email_text")
    today = reference_date or date.today()

    system = (
        "You extract application deadlines from emails for a student career platform. "
        f"Today is {today.isoformat()}. Resolve relative deadlines ('within 7 days', "
        "'next Friday') against that date and return ISO YYYY-MM-DD. "
        "Set has_deadline=false with deadline_date=null when no concrete deadline is "
        "stated — do not guess. Quote the exact source phrase in raw_deadline_text. "
        "Extract the APPLICATION deadline, not event or interview dates."
    )

    logger.info("Extracting deadline from %d chars of email text", len(text))
    return await _complete(
        response_model=DeadlineExtraction,
        system_prompt=system,
        user_prompt=f"Email text:\n\n{text}",
        operation="extract_deadline",
    )


async def generate_reminder(
    opportunity: Opportunity,
    *,
    days_remaining: int | None = None,
    student_name: str | None = None,
    deadline: DeadlineExtraction | None = None,
    extra_context: str | None = None,
) -> ReminderMessage:
    """Generate a deadline reminder for a student about one opportunity.

    Args:
        opportunity: The opportunity being reminded about.
        days_remaining: Days until the deadline. Inferred from ``deadline`` or
            ``opportunity.deadline`` when omitted.
        student_name: Recipient's name; the message stays generic if omitted.
        deadline: Optional richer deadline detail that overrides
            ``opportunity.deadline``.
        extra_context: Anything else worth mentioning, e.g. "resume incomplete".

    Returns:
        The generated :class:`ReminderMessage`.

    Raises:
        GroqConfigurationError: ``GROQ_API_KEY`` is missing.
        GroqTimeoutError: Groq did not respond in time.
        GroqRateLimitError: Groq rate limited the request.
        GroqExtractionError: Groq returned no valid structured response.
    """
    due = (deadline.deadline_date if deadline else None) or opportunity.deadline
    if days_remaining is None and due is not None:
        days_remaining = (due - date.today()).days

    system = (
        "You write short, warm, non-spammy deadline reminders for university students. "
        "Reference only the supplied facts — never invent deadlines, links, or perks. "
        "Keep the subject under 70 characters and the body under 120 words. "
        "Emit no placeholders such as [Name] or [Company]. "
        "Set urgency from days remaining: >14 low, 8-14 medium, 3-7 high, <3 critical."
    )

    details = [
        f"Title: {opportunity.title}",
        f"Organization: {opportunity.organization or 'unknown'}",
        f"Type: {opportunity.opportunity_type.value}",
        f"Deadline: {due.isoformat() if due else 'unknown'}",
        f"Days remaining: {days_remaining if days_remaining is not None else 'unknown'}",
        f"Recipient: {student_name or 'the student (address them generically)'}",
    ]
    if deadline and deadline.deadline_time:
        details.append(f"Deadline time: {deadline.deadline_time} {deadline.timezone or ''}".strip())
    if opportunity.application_url:
        details.append(f"Application link: {opportunity.application_url}")
    if opportunity.location:
        details.append(f"Location: {opportunity.location} ({opportunity.work_mode.value})")
    if extra_context:
        details.append(f"Additional context: {extra_context}")

    logger.info(
        "Generating reminder for '%s' (%s days remaining)",
        opportunity.title,
        days_remaining,
    )
    return await _complete(
        response_model=ReminderMessage,
        system_prompt=system,
        user_prompt="Write the reminder using these facts:\n" + "\n".join(details),
        operation="generate_reminder",
        temperature=0.4,
    )


async def extract_jd_skills(job_description: str) -> dict:
    """Extract required, preferred, and technology skills from a pasted JD.

    Groq is called through Instructor with a dedicated Pydantic response model,
    so callers always receive the three validated list fields required by the
    deterministic gap-analysis pipeline.
    """
    description = _require_text(job_description, "job_description")[:3000]
    system = (
        "Extract skills from job descriptions for a deterministic gap-analysis "
        "pipeline. Use only skills explicitly stated in the supplied description. "
        "Classify mandatory skills as required_skills, desirable or nice-to-have "
        "skills as preferred_skills, and named languages, frameworks, libraries, "
        "tools, databases, and platforms as tech_stack. Do not infer or invent "
        "skills. Return JSON only."
    )

    logger.info("Extracting JD skills from %d chars", len(description))
    result = await _complete(
        response_model=JDSkillsExtraction,
        system_prompt=system,
        user_prompt=(
            "Extract skills from this job description into required_skills, "
            f"preferred_skills, and tech_stack:\n\n{description}"
        ),
        operation="extract_jd_skills",
        model_name=GAP_ANALYSIS_MODEL,
    )
    return result.model_dump()


async def run_gap_analysis_llm(payload: dict) -> dict:
    """Synthesize explanations, resources, projects, and an assessment.

    The LLM receives only the gaps produced by deterministic scoring. Instructor
    validates the JSON structure, after which this function rejects any skill
    that was not present in the deterministic input.
    """
    if not isinstance(payload, dict):
        raise GroqInputError("payload must be a dictionary.")

    target_role = _require_text(payload.get("target_role"), "payload.target_role")
    raw_gaps = payload.get("gaps")
    if not isinstance(raw_gaps, list) or not raw_gaps:
        raise GroqInputError("payload.gaps must be a non-empty list.")

    # Retain only the deterministic fields produced by score_student_evidence;
    # unrelated caller data is never forwarded to the model as a gap.
    gaps: list[dict[str, Any]] = []
    gap_keys: set[str] = set()
    for gap in raw_gaps[:8]:
        if not isinstance(gap, dict):
            raise GroqInputError("Every payload.gaps item must be a dictionary.")
        skill = _require_text(gap.get("skill"), "payload.gaps[].skill")
        key = skill.lower()
        if key in gap_keys:
            continue
        gaps.append(
            {
                "skill": skill,
                "priority": gap.get("priority"),
                "cluster": gap.get("cluster"),
            }
        )
        gap_keys.add(key)

    if not gaps:
        raise GroqInputError("payload.gaps must contain at least one valid skill gap.")

    student_skills = payload.get("student_skills", [])
    if not isinstance(student_skills, list) or not all(
        isinstance(skill, str) for skill in student_skills
    ):
        raise GroqInputError("payload.student_skills must be a list of strings.")

    prompt = f"""You are a career advisor. A student's profile has been analysed against the role '{target_role}'.

The following skill gaps were deterministically identified:
{json.dumps(gaps, indent=2)}

The student's current skills: {", ".join(student_skills)}

Your task:
1. For every gap skill, write a 1-2 sentence explanation of WHY this skill matters for {target_role}.
2. Suggest exactly 3 projects the student can build to address multiple gaps. Be specific and practical.
3. For every gap skill, suggest at least 1 real learning resource with a real URL that starts with http.
4. Write a 2-3 sentence overall assessment of the student's readiness for {target_role}.

IMPORTANT: Only address the skills listed in the deterministic gaps above. Do NOT add, infer, rename, or substitute any gap skill. Project skills_addressed must also contain only those exact gap skills. Return JSON only matching the requested schema."""

    logger.info(
        "Generating gap analysis for %s with %d deterministic gaps",
        target_role,
        len(gaps),
    )
    result = await _complete(
        response_model=GapAnalysisLLMOutput,
        system_prompt=(
            "Follow the user's deterministic skill-gap list exactly. Never invent "
            "additional skills. Produce only valid JSON conforming to the response schema."
        ),
        user_prompt=prompt,
        operation="run_gap_analysis_llm",
        model_name=GAP_ANALYSIS_MODEL,
    )

    # Instructor validates shape and cardinality. This second guard validates
    # semantics: every input gap must be explained exactly once and projects may
    # reference no skill outside that authoritative set.
    returned_gap_keys = [item.skill.lower() for item in result.missing_skills]
    if (
        len(returned_gap_keys) != len(set(returned_gap_keys))
        or set(returned_gap_keys) != gap_keys
    ):
        raise GroqExtractionError(
            "run_gap_analysis_llm: response did not explain every deterministic gap exactly once."
        )

    if any(
        skill.lower() not in gap_keys
        for project in result.suggested_projects
        for skill in project.skills_addressed
    ):
        raise GroqExtractionError(
            "run_gap_analysis_llm: response invented a skill outside the deterministic gaps."
        )

    return result.model_dump()


def get_client() -> instructor.AsyncInstructor:
    """Return the lazily created, process-wide async Groq client.

    Raises:
        GroqConfigurationError: ``GROQ_API_KEY`` is not set.
    """
    global _client
    if _client is None:
        api_key = os.getenv(GROQ_API_KEY_ENV, "").strip()
        if not api_key:
            raise GroqConfigurationError(f"{GROQ_API_KEY_ENV} environment variable is not set.")
        _client = instructor.from_groq(
            groq.AsyncGroq(
                api_key=api_key,
                timeout=_env_float(GROQ_TIMEOUT_ENV, DEFAULT_TIMEOUT_SECONDS),
                # Transport-level retries; instructor retries validation failures.
                max_retries=_env_int(GROQ_MAX_RETRIES_ENV, DEFAULT_MAX_RETRIES),
            ),
            mode=instructor.Mode.JSON,
        )
        logger.info("Initialised Groq client (model=%s)", get_model())
    return _client


def reset_client() -> None:
    """Drop the cached client so the next call re-reads configuration."""
    global _client
    _client = None


def get_model() -> str:
    """Return the configured Groq model id."""
    return os.getenv(GROQ_MODEL_ENV, "").strip() or DEFAULT_MODEL


async def _complete(
    *,
    response_model: type[T],
    system_prompt: str,
    user_prompt: str,
    operation: str,
    temperature: float = DEFAULT_TEMPERATURE,
    model_name: str | None = None,
) -> T:
    """Run one structured Groq completion and map failures to service errors.

    Args:
        response_model: Pydantic model instructor must populate.
        system_prompt: Instructions defining the extraction contract.
        user_prompt: The content to operate on.
        operation: Label used in logs.
        temperature: Sampling temperature; extraction defaults to deterministic.
        model_name: Optional per-operation model override. Existing operations
            continue to use the configured default when omitted.

    Returns:
        The validated ``response_model`` instance.

    Raises:
        GroqConfigurationError: Credentials are missing or rejected.
        GroqTimeoutError: Groq did not respond in time.
        GroqRateLimitError: Groq rate limited the request.
        GroqExtractionError: Validation kept failing or Groq errored out.
    """
    client = get_client()
    selected_model = model_name or get_model()
    max_retries = _env_int(GROQ_MAX_RETRIES_ENV, DEFAULT_MAX_RETRIES)

    try:
        result: T = await client.chat.completions.create(
            model=selected_model,
            response_model=response_model,
            max_retries=max_retries,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except InstructorRetryException as exc:
        logger.error("%s: response failed validation after %d attempts", operation, max_retries)
        raise GroqExtractionError(
            f"{operation}: Groq did not return a valid {response_model.__name__} "
            f"after {max_retries} attempts."
        ) from exc
    except groq.APITimeoutError as exc:
        logger.error("%s: Groq request timed out", operation)
        raise GroqTimeoutError(f"{operation}: Groq request timed out.") from exc
    except groq.RateLimitError as exc:
        logger.warning("%s: Groq rate limit hit", operation)
        raise GroqRateLimitError(f"{operation}: Groq rate limit exceeded.") from exc
    except (groq.AuthenticationError, groq.PermissionDeniedError) as exc:
        logger.error("%s: Groq rejected the credentials", operation)
        raise GroqConfigurationError(f"{operation}: Groq rejected the API key.") from exc
    except groq.APIStatusError as exc:
        logger.error("%s: Groq returned HTTP %s", operation, exc.status_code)
        raise GroqExtractionError(f"{operation}: Groq returned HTTP {exc.status_code}.") from exc
    except groq.APIError as exc:
        logger.exception("%s: Groq request failed", operation)
        raise GroqExtractionError(f"{operation}: Groq request failed: {exc}") from exc
    except Exception as exc:  # instructor/pydantic surprises must not leak raw
        logger.exception("%s: unexpected failure", operation)
        raise GroqExtractionError(f"{operation}: unexpected failure: {exc}") from exc

    logger.info("%s: returned a valid %s", operation, response_model.__name__)
    return result


def _require_text(value: str, field_name: str) -> str:
    """Validate and truncate caller-supplied text.

    Raises:
        GroqInputError: ``value`` is not a non-empty string.
    """
    if not isinstance(value, str) or not value.strip():
        raise GroqInputError(f"{field_name} must be a non-empty string.")

    text = value.strip()
    if len(text) > MAX_INPUT_CHARS:
        logger.warning("%s truncated from %d to %d chars", field_name, len(text), MAX_INPUT_CHARS)
        text = text[:MAX_INPUT_CHARS]
    return text


def _clean_optional_str(value: Any) -> Any:
    """Normalise the placeholder strings LLMs emit instead of ``null``."""
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.lower() in {"", "null", "none", "n/a", "na", "unknown", "not specified"}:
            return None
        return cleaned
    return value


def _env_float(name: str, default: float) -> float:
    """Read a float env var, falling back to ``default`` when unset/invalid."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using %s", name, raw, default)
        return default


def _env_int(name: str, default: int) -> int:
    """Read an int env var, falling back to ``default`` when unset/invalid."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using %s", name, raw, default)
        return default
