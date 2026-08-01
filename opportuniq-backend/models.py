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


class SkillEvidence(BaseModel):
    """Deterministic evidence score for one required skill."""

    skill: str
    evidence_level: int
    evidence_summary: str
    jd_frequency: float
    priority: str
    learning_path_order: int
    cluster_name: str | None


class MissingSkill(BaseModel):
    """Validated narrative and resources for a deterministic skill gap."""

    skill: str
    priority: str
    reason: str
    evidence_level: int
    learning_path_order: int
    cluster_name: str | None
    learning_resources: list[dict]


class SuggestedProject(BaseModel):
    """Project recommendation addressing deterministic skill gaps."""

    project_type: str
    description: str
    skills_addressed: list[str]


class GapAnalysisResult(BaseModel):
    """Complete persisted output of the Gap Analysis Agent."""

    id: str
    profile_id: str
    target_role: str
    analysis_mode: str
    overall_assessment: str
    missing_skills: list[MissingSkill]
    suggested_projects: list[SuggestedProject]
    evidence_data: list[SkillEvidence]
    jd_snippet: str | None
    profile_snapshot: dict
    generated_at: str
    is_stale: bool
