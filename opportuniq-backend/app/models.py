"""Pydantic schemas for the OpportunIQ backend."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


OPPORTUNITY_TYPES = {
    "internship": "Internship",
    "full-time": "Full-time",
    "full time": "Full-time",
    "hackathon": "Hackathon",
    "all": "All",
}

DEADLINE_EVENT_TYPES = {
    "interview": "interview",
    "submission": "submission",
    "offer_acceptance": "offer_acceptance",
    "offer acceptance": "offer_acceptance",
    "application": "application",
    "assessment": "assessment",
    "registration": "registration",
    "joining": "joining",
    "other": "other",
}


def _strip_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def _require_non_empty(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Field cannot be empty.")
    return stripped


def _normalize_list(value: list[str]) -> list[str]:
    normalized = [item.strip() for item in value if item.strip()]
    if not normalized:
        raise ValueError("At least one value is required.")
    return normalized


def _normalize_opportunity_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = OPPORTUNITY_TYPES.get(value.strip().lower())
    if normalized is None:
        raise ValueError("Opportunity type must be Internship, Full-time, Hackathon, or All.")
    return normalized


def _non_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Value cannot be blank.")
    return stripped


def _clamp_score(value: float | int | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(float(value), 1.0))


def _normalize_deadline_event_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = DEADLINE_EVENT_TYPES.get(value.strip().lower().replace("-", "_"))
    if normalized is None:
        raise ValueError(
            "Event type must be interview, submission, offer_acceptance, "
            "application, assessment, registration, joining, or other."
        )
    return normalized


class ResumeAIData(BaseModel):
    """Structured profile data returned by the ResumeAI service."""

    full_name: str | None = None
    year_of_study: str | None = None
    graduation_year: int | None = None
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    preferred_location: str | None = None
    opportunity_type: str | None = None


class ResumeAIResponse(BaseModel):
    """Response envelope from the ResumeAI service."""

    success: bool
    data: ResumeAIData | None = None
    error: str | None = None


class StudentProfile(BaseModel):
    """Student profile used for opportunity matching."""

    profile_id: str | None = None
    id: int | None = None
    name: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    year_of_study: str | None = None
    graduation_year: int | None = None
    degree: str | None = None
    college: str | None = None
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    location: str | None = None
    preferred_location: str | None = None
    opportunity_type: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Opportunity(BaseModel):
    """Opportunity candidate discovered from an external source."""

    id: int | None = None
    source: str
    external_id: str | None = None
    title: str
    organization: str | None = None
    location: str | None = None
    url: HttpUrl | None = None
    description: str | None = None
    deadline: date | datetime | None = None
    opportunity_type: str | None = None
    skills: list[str] = Field(default_factory=list)
    match_score: float | None = None
    created_at: datetime | None = None


class DeadlineExtraction(BaseModel):
    """Deadline details extracted from an email or opportunity."""

    has_deadline: bool
    deadline_date: date | None = None
    deadline_time: str | None = None
    event_type: str | None = None
    organization: str | None = None
    action_required: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_message_id: str | None = None


class ReminderMessage(BaseModel):
    """Reminder text scheduled for a deadline."""

    deadline_id: int
    channel: Literal["websocket", "email"]
    message: str
    scheduled_for: datetime
    sent_at: datetime | None = None
    status: str = "pending"


class ManualProfileCreate(BaseModel):
    """Request body for manual profile creation."""

    name: str
    email: str
    year_of_study: str
    graduation_year: int | None = None
    degree: str
    college: str
    skills: list[str]
    target_roles: list[str]
    location: str
    opportunity_type: str

    @field_validator("name", "email", "year_of_study", "degree", "college", "location")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_non_empty(value)

    @field_validator("skills", "target_roles")
    @classmethod
    def validate_required_list(cls, value: list[str]) -> list[str]:
        return _normalize_list(value)

    @field_validator("opportunity_type")
    @classmethod
    def validate_opportunity_type(cls, value: str) -> str:
        return _normalize_opportunity_type(value) or value


class ProfileUpdate(BaseModel):
    """Request body for partial profile updates."""

    name: str | None = None
    email: str | None = None
    year_of_study: str | None = None
    graduation_year: int | None = None
    degree: str | None = None
    college: str | None = None
    skills: list[str] | None = None
    target_roles: list[str] | None = None
    location: str | None = None
    opportunity_type: str | None = None

    @field_validator("name", "email", "year_of_study", "degree", "college", "location")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return _strip_text(value)

    @field_validator("skills", "target_roles")
    @classmethod
    def strip_optional_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [item.strip() for item in value if item.strip()]

    @field_validator("opportunity_type")
    @classmethod
    def normalize_optional_opportunity_type(cls, value: str | None) -> str | None:
        return _normalize_opportunity_type(value)


class ProfileResponse(BaseModel):
    """Profile response returned by the Profile API."""

    profile_id: str
    name: str | None = None
    email: str | None = None
    year_of_study: str | None = None
    graduation_year: int | None = None
    degree: str | None = None
    college: str | None = None
    skills: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    location: str | None = None
    opportunity_type: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class ProfileCreateResponse(BaseModel):
    """Response returned after a profile is created."""

    profile_id: str
    profile: ProfileResponse
    missing_fields: list[str] = Field(default_factory=list)


class ProfileUpdateResponse(BaseModel):
    """Response returned after a profile is updated."""

    success: bool
    profile: ProfileResponse
    missing_fields: list[str] = Field(default_factory=list)


class OpportunitySearchRequest(BaseModel):
    """Request body for opportunity discovery."""

    profile_id: str
    force_refresh: bool = False

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        return _non_blank(value)


class OpportunitySearchResponse(BaseModel):
    """Response returned when opportunity discovery starts or uses cache."""

    session_id: str
    status: str
    cached: bool = False
    result_count: int = 0
    errors: list[str] = Field(default_factory=list)


class OpportunityResponse(BaseModel):
    """Persisted opportunity returned by the Opportunity API."""

    opportunity_id: str
    session_id: str
    profile_id: str
    title: str
    company: str
    platform: str
    url: str
    location: str | None = None
    deadline: date | str | None = None
    stipend_or_prize: str | None = None
    eligibility: str | None = None
    skills_required: list[str] = Field(default_factory=list)
    description: str | None = None
    also_on: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    urgency_score: float = 0.0
    combined_score: float = 0.0
    is_expired: bool = False
    fetched_at: datetime | str | None = None

    @field_validator("match_score", "urgency_score", "combined_score", mode="before")
    @classmethod
    def validate_scores(cls, value: float | int | None) -> float:
        return _clamp_score(value)


class OpportunityListResponse(BaseModel):
    """List response for persisted opportunities."""

    opportunities: list[OpportunityResponse]
    count: int
    session_id: str | None = None
    profile_id: str | None = None


class AgentTraceEvent(BaseModel):
    """Trace event streamed to the frontend while discovery runs."""

    session_id: str
    agent: str
    status: str
    message: str
    timestamp: datetime | str
    metadata: dict = Field(default_factory=dict)

    @field_validator("session_id", "agent", "status", "message")
    @classmethod
    def validate_trace_text(cls, value: str) -> str:
        return _non_blank(value)


class DeadlineCreate(BaseModel):
    """Request body for creating a manual deadline."""

    profile_id: str
    opportunity_id: str | None = None
    title: str
    organization: str | None = None
    deadline_datetime: datetime
    event_type: str = "other"
    action_required: str | None = None
    notes: str | None = None

    @field_validator("profile_id", "title")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _non_blank(value)

    @field_validator("opportunity_id", "organization", "action_required", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return _strip_text(value)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        return _normalize_deadline_event_type(value) or "other"


class DeadlineUpdate(BaseModel):
    """Request body for updating a deadline."""

    opportunity_id: str | None = None
    title: str | None = None
    organization: str | None = None
    deadline_datetime: datetime | None = None
    event_type: str | None = None
    action_required: str | None = None
    notes: str | None = None
    needs_review: bool | None = None
    is_completed: bool | None = None
    is_cancelled: bool | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _non_blank(value)

    @field_validator("opportunity_id", "organization", "action_required", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return _strip_text(value)

    @field_validator("event_type")
    @classmethod
    def validate_optional_event_type(cls, value: str | None) -> str | None:
        return _normalize_deadline_event_type(value)


class DeadlineResponse(BaseModel):
    """Deadline registry item returned by the Deadline API."""

    deadline_id: str
    profile_id: str
    opportunity_id: str | None = None
    title: str
    organization: str | None = None
    deadline_datetime: datetime | str | None = None
    event_type: str | None = None
    action_required: str | None = None
    notes: str | None = None
    source: str
    gmail_message_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    needs_review: bool = False
    is_completed: bool = False
    is_cancelled: bool = False
    status: str
    days_remaining: int | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class DeadlineCreateResponse(BaseModel):
    """Response returned after creating a deadline."""

    success: bool
    deadline: DeadlineResponse
    reminders_scheduled: list[str] = Field(default_factory=list)


class DeadlineUpdateResponse(BaseModel):
    """Response returned after updating a deadline."""

    success: bool
    deadline: DeadlineResponse


class DeadlineListResponse(BaseModel):
    """List response for deadline registry queries."""

    deadlines: list[DeadlineResponse]
    count: int
    profile_id: str | None = None


class DeadlineDeleteResponse(BaseModel):
    """Response returned after deleting a deadline."""

    success: bool
    deadline_id: str


class CalendarEventResponse(BaseModel):
    """Calendar event projection for a deadline."""

    id: str
    title: str
    start: datetime | str
    end: datetime | str
    color: str
    deadline: DeadlineResponse


class GmailScanRequest(BaseModel):
    """Request body for triggering a Gmail deadline scan."""

    profile_id: str

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        return _non_blank(value)


class GmailStatusResponse(BaseModel):
    """Gmail connection status for a profile."""

    connected: bool
    profile_id: str
    email: str | None = None
    last_scanned: datetime | str | None = None
    deadlines_found: int = Field(default=0, ge=0)


class GmailScanResponse(BaseModel):
    """Response returned when a Gmail scan is started."""

    profile_id: str
    session_id: str
    status: str
    emails_scanned: int = Field(default=0, ge=0)
    deadlines_found: int = Field(default=0, ge=0)
    needs_review: int = Field(default=0, ge=0)
    errors: list[str] = Field(default_factory=list)


class GmailDisconnectResponse(BaseModel):
    """Response returned after disconnecting Gmail."""

    success: bool
    profile_id: str
