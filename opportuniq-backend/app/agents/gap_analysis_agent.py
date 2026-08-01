"""Active-package orchestration adapter for Person C's Gap Analysis pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.models import GapAnalysisResult
from app.repositories import (
    gap_analysis_repository,
    opportunity_repository,
    profile_repository,
)
from app.services import gap_analysis_service, groq_service
from app.websocket_manager import emit_trace


AGENT_NAME = "Gap Analysis Agent"


async def run(
    profile_id: str,
    target_role: str | None = None,
    job_description: str | None = None,
    opportunity_id: str | None = None,
    session_id: str | None = None,
) -> GapAnalysisResult:
    """Run Person C's validated pipeline through active data boundaries."""
    trace_session_id = session_id or profile_id
    await _trace(trace_session_id, "Loading student profile...")

    profile = await profile_repository.get_profile_by_id(profile_id)
    if profile is None:
        raise ValueError("Profile not found")

    student_skills = _string_list(profile.get("skills"))
    target_roles = _string_list(profile.get("target_roles"))
    effective_role = target_role or (target_roles[0] if target_roles else None)

    opportunity: dict[str, Any] | None = None
    opportunity_skills: list[str] | None = None
    if opportunity_id:
        opportunity = await opportunity_repository.get_opportunity_by_id(opportunity_id)
        if opportunity is None:
            raise ValueError("Opportunity not found")
        opportunity_skills = _string_list(opportunity.get("skills_required"))
        effective_role = effective_role or str(opportunity.get("title") or "").strip() or None

    effective_role = effective_role or "Software Engineer"
    await _trace(trace_session_id, "Determining required skills...")

    jd_extracted = None
    if job_description:
        jd_extracted = await groq_service.extract_jd_skills(job_description)

    required_skills = gap_analysis_service.determine_required_skills(
        effective_role,
        jd_extracted,
        opportunity_skills,
    )
    if not required_skills:
        raise ValueError("Could not determine required skills for this role")

    await _trace(trace_session_id, "Scoring your profile against required skills...")
    evidence = gap_analysis_service.score_student_evidence(required_skills, student_skills)
    deterministic_gaps = [item for item in evidence if item.evidence_level == 0][:8]

    await _trace(trace_session_id, "Generating improvement recommendations...")
    llm_result = await groq_service.run_gap_analysis_llm(
        {
            "target_role": effective_role,
            "student_skills": student_skills,
            "gaps": [
                {
                    "skill": gap.skill,
                    "priority": gap.priority,
                    "cluster": gap.cluster_name,
                }
                for gap in deterministic_gaps
            ],
        }
    )
    missing_skills, suggested_projects = gap_analysis_service.normalize_llm_output(
        llm_result,
        evidence,
    )

    analysis_mode = (
        "profile_vs_opportunity"
        if opportunity_id
        else "profile_vs_jd"
        if job_description
        else "profile_vs_role"
    )
    result = GapAnalysisResult(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        opportunity_id=opportunity_id,
        target_role=effective_role,
        analysis_mode=analysis_mode,
        overall_assessment=llm_result.get("overall_assessment")
        or f"Analysis complete for {effective_role}.",
        missing_skills=[_model_dump(item) for item in missing_skills],
        suggested_projects=[_model_dump(item) for item in suggested_projects],
        evidence_data=[_model_dump(item) for item in evidence],
        jd_snippet=job_description[:300] if job_description else None,
        profile_snapshot={
            "skills_count": len(student_skills),
            "target_roles": target_roles,
            "opportunity_title": opportunity.get("title") if opportunity else None,
        },
        generated_at=datetime.now(UTC),
        is_stale=False,
    )

    await _trace(trace_session_id, "Saving analysis...")
    persisted = await gap_analysis_repository.save_gap_analysis(
        result,
        persist=analysis_mode != "profile_vs_jd",
    )
    final_result = GapAnalysisResult(**persisted)

    await emit_trace(
        trace_session_id,
        AGENT_NAME,
        "complete",
        f"Gap analysis complete — {len(final_result.missing_skills)} skill gaps identified",
    )
    return final_result


async def _trace(session_id: str, message: str) -> None:
    """Emit one Person C pipeline progress event."""
    await emit_trace(session_id, AGENT_NAME, "running", message)


def _string_list(value: Any) -> list[str]:
    """Adapt active repository list fields to the validated service input."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _model_dump(value: Any) -> dict[str, Any]:
    """Adapt Person C Pydantic results to active Pydantic schemas."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()
