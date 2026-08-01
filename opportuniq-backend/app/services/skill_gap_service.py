"""Exact and semantic skill-gap analysis with lazy model loading."""

import asyncio
import re
from typing import Any

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def normalize_skill(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _unique(values: list[str]) -> list[tuple[str, str]]:
    result = []; seen = set()
    for value in values:
        normalized = normalize_skill(value)
        if normalized and normalized not in seen:
            seen.add(normalized); result.append((normalized, str(value).strip()))
    return result


def cosine_score(skill_a: str, skill_b: str) -> float:
    from sentence_transformers import util
    embeddings = get_embedding_model().encode([skill_a, skill_b], convert_to_tensor=True)
    return max(0.0, min(1.0, float(util.cos_sim(embeddings[0], embeddings[1]).item())))


async def calculate_skill_gap(*, opportunity: dict[str, Any], profile: dict[str, Any], partial_threshold: float = 0.70) -> dict[str, Any]:
    required = _unique(opportunity.get("skills_required") or [])
    student = _unique(profile.get("skills") or [])
    if not required:
        return {"matched": [], "partial": [], "missing": [], "match_percentage": 100.0}
    student_map = dict(student); matched = []; partial = []; missing = []; weighted = 0.0
    for normalized, readable in required:
        if normalized in student_map:
            matched.append(normalized); weighted += 1.0; continue
        best_name = None; best_score = 0.0
        for student_normalized, student_readable in student:
            score = await asyncio.to_thread(cosine_score, normalized, student_normalized)
            if score > best_score: best_name, best_score = student_readable, score
        if best_name is not None and best_score >= partial_threshold:
            partial.append({"required": readable, "matched_as": best_name, "similarity": round(best_score, 4)}); weighted += best_score
        else: missing.append(readable)
    return {"matched": matched, "partial": partial, "missing": missing, "match_percentage": round(max(0.0, min(100.0, weighted / len(required) * 100)), 2)}
