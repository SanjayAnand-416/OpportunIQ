"""Pydantic schemas for the OpportunIQ backend."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


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

    id: int | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    year_of_study: str | None = None
    graduation_year: int | None = None
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
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
