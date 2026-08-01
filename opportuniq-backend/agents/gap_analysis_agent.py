"""Gap Analysis Agent orchestration pipeline from Build Plan Step 3.5."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import aiosqlite

from app.database import DATABASE_PATH
from app.websocket_manager import emit_trace
from models import GapAnalysisResult
from services.gap_analysis_service import (
    determine_required_skills,
    normalize_llm_output,
    score_student_evidence,
)
from services.groq_service import extract_jd_skills, run_gap_analysis_llm


AGENT_NAME = "Gap Analysis Agent"


def _deserialize_string_list(value: str | None) -> list[str]:
    """Decode a SQLite JSON list into clean strings.

    Profile and opportunity list fields are stored as JSON text. Treat empty or
    legacy malformed values as empty lists rather than leaking JSON errors from
    the orchestration layer.
    """
    if not value:
        return []
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(decoded, list):
        return []
    return [str(item) for item in decoded]


def _model_dump(model: Any) -> dict[str, Any]:
    """Serialize Pydantic v2 models while tolerating v1-compatible models."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


async def run(
    profile_id: str,
    target_role: str | None = None,
    job_description: str | None = None,
    opportunity_id: str | None = None,
    session_id: str | None = None,
) -> GapAnalysisResult:
    """Run and persist one deterministic-first gap analysis.

    Supports profile-vs-role, profile-vs-JD, and profile-vs-opportunity modes.
    The LLM receives only the deterministic gaps produced by evidence scoring;
    its response is normalized before it can enter the persisted result.
    """
    trace_session_id = session_id or profile_id

    # 1. Load the profile that owns the analysis.
    await emit_trace(
        trace_session_id,
        AGENT_NAME,
        "running",
        "Loading student profile...",
    )

    async with aiosqlite.connect(DATABASE_PATH) as db:
        profile_cursor = await db.execute(
            """
            SELECT skills, target_roles
            FROM student_profiles
            WHERE profile_id = ? OR CAST(id AS TEXT) = ?
            LIMIT 1
            """,
            [profile_id, profile_id],
        )
        profile_row = await profile_cursor.fetchone()
        if not profile_row:
            raise ValueError("Profile not found")

        student_skills = _deserialize_string_list(profile_row[0])
        target_roles = _deserialize_string_list(profile_row[1])
        effective_role = target_role or (target_roles[0] if target_roles else None)

        # 2. Opportunity mode supplies the highest-priority required skills.
        opportunity_skills = None
        opportunity_title = None
        if opportunity_id:
            opportunity_cursor = await db.execute(
                """
                SELECT skills_required, title
                FROM opportunities
                WHERE opportunity_id = ? OR CAST(id AS TEXT) = ?
                LIMIT 1
                """,
                [opportunity_id, opportunity_id],
            )
            opportunity_row = await opportunity_cursor.fetchone()
            if not opportunity_row:
                raise ValueError("Opportunity not found")
            opportunity_skills = _deserialize_string_list(opportunity_row[0])
            opportunity_title = opportunity_row[1]
            effective_role = effective_role or opportunity_title

    effective_role = effective_role or "Software Engineer"

    await emit_trace(
        trace_session_id,
        AGENT_NAME,
        "running",
        "Determining required skills...",
    )

    # 3. JD mode extracts structured skill categories before deterministic
    # source-priority resolution.
    jd_extracted = None
    if job_description:
        jd_extracted = await extract_jd_skills(job_description)

    # 4. Required skills follow the strict opportunity > JD > taxonomy order.
    required_skills = determine_required_skills(
        effective_role,
        jd_extracted,
        opportunity_skills,
    )
    if not required_skills:
        raise ValueError("Could not determine required skills for this role")

    await emit_trace(
        trace_session_id,
        AGENT_NAME,
        "running",
        "Scoring your profile against required skills...",
    )

    # 5-6. Score profile evidence deterministically and cap the authoritative
    # missing-skill set at the Build Plan limit of eight.
    evidence = score_student_evidence(required_skills, student_skills)
    deterministic_gaps = [item for item in evidence if item.evidence_level == 0][:8]

    await emit_trace(
        trace_session_id,
        AGENT_NAME,
        "running",
        "Generating improvement recommendations...",
    )

    # 7. The narrative LLM receives only deterministic gap skills and their
    # deterministic priority/cluster metadata.
    llm_payload = {
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
    llm_result = await run_gap_analysis_llm(llm_payload)

    # 8. Apply the hallucination guard before constructing the API model.
    missing_skills, suggested_projects = normalize_llm_output(llm_result, evidence)

    # 9. Create the canonical result for the selected comparison mode.
    analysis_mode = (
        "profile_vs_opportunity"
        if opportunity_id
        else "profile_vs_jd"
        if job_description
        else "profile_vs_role"
    )
    # Reuse the existing logical analysis row ID. SQLite's OR REPLACE operates
    # on keys, so a fresh UUID would otherwise create duplicate analyses.
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if opportunity_id:
            existing_cursor = await db.execute(
                """
                SELECT id
                FROM gap_analyses
                WHERE profile_id = ? AND opportunity_id = ?
                LIMIT 1
                """,
                [profile_id, opportunity_id],
            )
        else:
            existing_cursor = await db.execute(
                """
                SELECT id
                FROM gap_analyses
                WHERE profile_id = ?
                  AND opportunity_id IS NULL
                  AND analysis_mode = ?
                  AND target_role = ?
                LIMIT 1
                """,
                [profile_id, analysis_mode, effective_role],
            )
        existing_row = await existing_cursor.fetchone()

    analysis_id = existing_row[0] if existing_row else str(uuid.uuid4())
    result = GapAnalysisResult(
        id=analysis_id,
        profile_id=profile_id,
        target_role=effective_role,
        analysis_mode=analysis_mode,
        overall_assessment=llm_result.get("overall_assessment")
        or f"Analysis complete for {effective_role}.",
        missing_skills=missing_skills,
        suggested_projects=suggested_projects,
        evidence_data=evidence,
        jd_snippet=job_description[:300] if job_description else None,
        profile_snapshot={
            "skills_count": len(student_skills),
            "target_roles": target_roles,
            "opportunity_title": opportunity_title,
        },
        generated_at=datetime.now().isoformat(),
        is_stale=False,
    )

    await emit_trace(
        trace_session_id,
        AGENT_NAME,
        "running",
        "Saving analysis...",
    )

    # 10. Persist the normalized result in the Step 3.5 gap_analyses table.
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO gap_analyses
            (id, profile_id, opportunity_id, target_role, analysis_mode,
             overall_assessment, missing_skills, suggested_projects,
             evidence_data, jd_snippet, profile_snapshot, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                result.id,
                profile_id,
                opportunity_id,
                effective_role,
                analysis_mode,
                result.overall_assessment,
                json.dumps([_model_dump(item) for item in missing_skills]),
                json.dumps([_model_dump(item) for item in suggested_projects]),
                json.dumps([_model_dump(item) for item in evidence]),
                result.jd_snippet,
                json.dumps(result.profile_snapshot),
                result.generated_at,
            ],
        )
        await db.commit()

    # 11. Publish the terminal trace only after SQLite commits successfully.
    await emit_trace(
        trace_session_id,
        AGENT_NAME,
        "complete",
        f"Gap analysis complete — {len(missing_skills)} skill gaps identified",
    )
    return result
