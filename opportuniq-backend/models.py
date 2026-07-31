"""Pydantic domain models for OpportunIQ."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EducationEntry(BaseModel):
    """A single education record extracted from a resume."""

    degree: str | None = None
    institution: str | None = None
    field_of_study: str | None = None
    start_year: str | None = None
    end_year: str | None = None
    grade: str | None = None


class ExperienceEntry(BaseModel):
    """A single work/internship record extracted from a resume."""

    title: str | None = None
    organization: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class ProjectEntry(BaseModel):
    """A single project record extracted from a resume."""

    name: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class StudentProfile(BaseModel):
    """Canonical student profile used across OpportunIQ modules."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
