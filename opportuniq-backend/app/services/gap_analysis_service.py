"""Active adapter for Person C's deterministic Gap Analysis service."""

from __future__ import annotations

import importlib
import logging
import sys
import threading
from typing import Any

import numpy as np

from app.services.ranker_service import BUNDLED_MODEL_PATH


logger = logging.getLogger(__name__)
_IMPORT_LOCK = threading.Lock()


class _UnavailableEmbeddingModel:
    """Signal that the packaged semantic model could not be loaded."""

    def encode(self, _sentences: list[str]) -> Any:
        raise RuntimeError("Packaged MiniLM model is unavailable")


class _DeterministicEmbeddingModel:
    """Disable semantic matches while retaining Person C's exact-match logic."""

    def encode(self, sentences: list[str]) -> Any:
        return np.zeros((len(sentences), 1), dtype=float)

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
    service = _person_c_gap_service()
    try:
        return service.score_student_evidence(required_skills, student_skills)
    except Exception as exc:
        logger.warning(
            "Packaged MiniLM evidence scoring unavailable; using exact-match fallback: %s",
            type(exc).__name__,
        )
        service.model = _DeterministicEmbeddingModel()
        return service.score_student_evidence(required_skills, student_skills)


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
    """Resolve Person C with MiniLM redirected to the bundled local snapshot."""
    module_name = "services.gap_analysis_service"
    if module_name in sys.modules:
        return sys.modules[module_name]

    with _IMPORT_LOCK:
        if module_name in sys.modules:
            return sys.modules[module_name]

        import sentence_transformers

        original_constructor = sentence_transformers.SentenceTransformer

        def packaged_constructor(model_name: str, *args: Any, **kwargs: Any) -> Any:
            if model_name != "all-MiniLM-L6-v2":
                return original_constructor(model_name, *args, **kwargs)
            if not BUNDLED_MODEL_PATH.is_dir():
                logger.warning("Packaged MiniLM directory is missing")
                return _UnavailableEmbeddingModel()
            try:
                return original_constructor(
                    str(BUNDLED_MODEL_PATH),
                    *args,
                    local_files_only=True,
                    **kwargs,
                )
            except Exception as exc:
                logger.warning("Packaged MiniLM could not be loaded: %s", type(exc).__name__)
                return _UnavailableEmbeddingModel()

        sentence_transformers.SentenceTransformer = packaged_constructor
        try:
            return importlib.import_module(module_name)
        finally:
            sentence_transformers.SentenceTransformer = original_constructor
