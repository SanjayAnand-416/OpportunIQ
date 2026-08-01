"""Active adapter for Person C's deterministic Gap Analysis service."""

from __future__ import annotations

import importlib
from typing import Any


def determine_required_skills(
    target_role: str | None,
    jd_extracted: dict[str, Any] | None,
    opportunity_skills: list[str] | None,
) -> list[dict[str, Any]]:
    """Delegate required-skill selection without changing its methodology."""
    return _person_c_gap_service().determine_required_skills(
        target_role,
        jd_extracted,
        opportunity_skills,
    )


def score_student_evidence(
    required_skills: list[dict[str, Any]],
    student_skills: list[str],
) -> list[Any]:
    """Delegate deterministic MiniLM evidence scoring unchanged."""
    return _person_c_gap_service().score_student_evidence(required_skills, student_skills)


def normalize_llm_output(
    llm_result: dict[str, Any],
    deterministic_gaps: list[Any],
) -> tuple[list[Any], list[Any]]:
    """Delegate Person C's hallucination guard unchanged."""
    return _person_c_gap_service().normalize_llm_output(
        llm_result,
        deterministic_gaps,
    )


def _person_c_gap_service() -> Any:
    """Resolve the legacy implementation only at the adapter boundary."""
    return importlib.import_module("services.gap_analysis_service")
