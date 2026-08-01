"""Deterministic skill-gap analysis and LLM output normalization.

This service preserves the ResumeAI methodology described in Build Plan Step
3.5: determine required skills first, score profile evidence deterministically,
and accept LLM output only after validating it against those scores.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from models import MissingSkill, SkillEvidence, SuggestedProject


# Resolve the taxonomy relative to the repository so importing this service is
# independent of the process's current working directory. The taxonomy is read
# once and then reused for every analysis.
TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "data" / "skills_taxonomy.json"
with TAXONOMY_PATH.open(encoding="utf-8") as taxonomy_file:
    TAXONOMY: dict[str, Any] = json.load(taxonomy_file)

# Step 3.5 specifies this exact sentence-transformer model for semantic evidence
# checks. It is initialized once rather than once per required skill.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
SEMANTIC_SIMILARITY_THRESHOLD = 0.75
model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def determine_required_skills(
    target_role: str | None,
    jd_extracted: dict | None,
    opportunity_skills: list | None,
) -> list[dict]:
    """Return at most 20 required skills with deterministic frequencies.

    Sources are considered in strict priority order: direct opportunity skills,
    extracted job-description skills, then the role taxonomy. Required and
    opportunity skills receive 1.0, JD tech-stack skills 0.8, and JD preferred
    skills 0.7.
    """
    # Opportunity mode has the highest priority. Every explicitly supplied
    # opportunity skill is required.
    if opportunity_skills:
        return [{"skill": skill, "frequency": 1.0} for skill in opportunity_skills[:20]]

    # JD mode retains category order and the strongest frequency when a skill
    # appears in more than one category.
    if jd_extracted:
        skills: list[dict] = []
        seen: set[str] = set()

        # Categories are processed from strongest to weakest frequency. This
        # makes the first occurrence authoritative while deduplicating both
        # within and across categories case-insensitively.
        categories = (
            ("required_skills", 1.0),
            ("tech_stack", 0.8),
            ("preferred_skills", 0.7),
        )
        for category, frequency in categories:
            values = jd_extracted.get(category)
            if not isinstance(values, (list, tuple)):
                continue
            for value in values:
                if not isinstance(value, str):
                    continue
                skill = value.strip()
                key = skill.lower()
                if not skill or key in seen:
                    continue
                skills.append({"skill": skill, "frequency": frequency})
                seen.add(key)

        return skills[:20]

    # Target-role mode performs the substring matching specified by Step 3.5,
    # allowing inputs such as "Junior SDE Intern" to match "sde intern".
    if target_role:
        role_key = target_role.lower().strip()
        matched_pattern = None

        for pattern in TAXONOMY["role_patterns"]:
            if pattern in role_key or role_key in pattern:
                matched_pattern = pattern
                break

        if matched_pattern:
            return [
                {"skill": skill, "frequency": 1.0}
                for skill in TAXONOMY["role_patterns"][matched_pattern][:20]
            ]

        # Unknown roles use the generic professional-skill fallback from the
        # Build Plan at its prescribed 0.8 frequency.
        return [
            {"skill": skill, "frequency": 0.8}
            for skill in [
                "Python",
                "Git",
                "SQL",
                "Communication",
                "Problem Solving",
            ]
        ]

    return []


def score_student_evidence(
    required_skills: list[dict],
    student_skills: list[str],
) -> list[SkillEvidence]:
    """Score profile evidence for each required skill deterministically.

    Evidence level 1 means the skill is explicitly present or semantically
    similar to the profile at a cosine similarity above 0.75. Evidence level 0
    means no such evidence was found. Priority, cluster, and learning-path order
    are derived only from deterministic inputs and the taxonomy.
    """
    synonyms: dict[str, str] = TAXONOMY.get("skill_synonyms", {})

    # Canonicalize profile skills so aliases such as "js" and "JavaScript"
    # compare identically. All comparison values remain lowercase.
    student_lower = [skill.lower() for skill in student_skills]
    student_canonical = {synonyms.get(skill, skill).lower() for skill in student_lower}
    evidence_list: list[SkillEvidence] = []

    # The Build Plan compares each required skill with a single embedding of the
    # complete profile skill list. Compute that profile embedding once.
    student_embedding = None
    if student_skills:
        student_embedding = model.encode([" ".join(student_skills)])[0]

    for required in required_skills:
        skill = required["skill"]
        frequency = required["frequency"]
        skill_lower = skill.lower()
        canonical_skill = synonyms.get(skill_lower, skill).lower()

        # Exact and synonym-aware presence is deterministic evidence level 1.
        if skill_lower in student_lower or canonical_skill in student_canonical:
            evidence_level = 1
            evidence_summary = f"'{skill}' is listed in your profile skills"
        else:
            # When exact matching fails, apply the specified MiniLM cosine
            # similarity enrichment. The threshold is strictly greater than
            # 0.75, matching Step 3.5.
            if student_embedding is not None:
                skill_embedding = model.encode([skill])[0]
                similarity = float(
                    cosine_similarity([skill_embedding], [student_embedding])[0][0]
                )
            else:
                similarity = 0.0

            if similarity > SEMANTIC_SIMILARITY_THRESHOLD:
                evidence_level = 1
                evidence_summary = f"'{skill}' is similar to skills in your profile"
            else:
                evidence_level = 0
                evidence_summary = f"'{skill}' was not found in your profile"

        # Priority follows the exact evidence/frequency branches in Step 3.5.
        if evidence_level == 0 and frequency >= 0.8:
            priority = "high"
        elif evidence_level == 0 and frequency < 0.8:
            priority = "medium"
        elif evidence_level == 1 and frequency >= 0.9:
            priority = "medium"
        else:
            priority = "low"

        # Use the canonical taxonomy entry for aliases, falling back to General
        # for skills extracted from opportunities or JDs that are not catalogued.
        canonical_name = synonyms.get(skill_lower, skill)
        cluster_name = TAXONOMY["skill_clusters"].get(canonical_name, "General")

        # Skills with declared prerequisites follow foundation skills in the
        # learning path, exactly as prescribed by the Build Plan.
        prerequisites = TAXONOMY.get("prerequisites", {})
        learning_path_order = 1 if canonical_name not in prerequisites else 2

        evidence_list.append(
            SkillEvidence(
                skill=skill,
                evidence_level=evidence_level,
                evidence_summary=evidence_summary,
                jd_frequency=frequency,
                priority=priority,
                learning_path_order=learning_path_order,
                cluster_name=cluster_name,
            )
        )

    # Stable sorting preserves source order among equal-priority/equal-frequency
    # entries: high first, medium second, low last, then frequency descending.
    evidence_list.sort(
        key=lambda item: (
            item.priority != "high",
            item.priority != "medium",
            -item.jd_frequency,
        )
    )
    return evidence_list


def normalize_llm_output(
    llm_result: dict,
    deterministic_gaps: list[SkillEvidence],
) -> tuple[list[MissingSkill], list[SuggestedProject]]:
    """Apply the hallucination guard to an LLM-generated gap narrative.

    Only deterministic level-0 gaps survive. Deterministic priority, evidence,
    cluster, and learning order replace any LLM-provided values, and output
    follows deterministic gap order. Missing skills, projects, and resources are
    capped at 8, 3, and 5 respectively.
    """
    deterministic_missing = [
        evidence for evidence in deterministic_gaps if evidence.evidence_level == 0
    ]
    deterministic_by_skill = {
        evidence.skill.lower(): evidence for evidence in deterministic_missing
    }
    valid_gap_skills = set(deterministic_by_skill)

    # Index the first LLM narrative for each skill. Invented skills are never
    # entered because they have no deterministic level-0 evidence.
    llm_missing_by_skill: dict[str, dict] = {}
    for candidate in llm_result.get("missing_skills", []):
        if not isinstance(candidate, dict):
            continue
        candidate_key = str(candidate.get("skill", "")).lower()
        if (
            candidate_key in valid_gap_skills
            and candidate_key not in llm_missing_by_skill
        ):
            llm_missing_by_skill[candidate_key] = candidate

    missing: list[MissingSkill] = []

    # Iterate deterministic evidence—not LLM order—to preserve the authoritative
    # sorting produced by score_student_evidence().
    for deterministic in deterministic_missing:
        if len(missing) == 8:
            break

        skill_key = deterministic.skill.lower()
        candidate = llm_missing_by_skill.get(skill_key)
        if candidate is None:
            continue

        # Keep at most the first five resources and discard malformed entries or
        # URLs that do not begin with "http".
        resources = [
            resource
            for resource in candidate.get("learning_resources", [])[:5]
            if isinstance(resource, dict)
            and str(resource.get("url", "")).startswith("http")
        ]

        missing.append(
            MissingSkill(
                skill=deterministic.skill,
                priority=deterministic.priority,
                reason=candidate.get("reason")
                or (
                    f"'{deterministic.skill}' is required for this role and "
                    "not present in your profile."
                ),
                evidence_level=deterministic.evidence_level,
                learning_path_order=deterministic.learning_path_order,
                cluster_name=deterministic.cluster_name,
                learning_resources=resources,
            )
        )

    # Projects may contain narrative text, but every referenced skill must be a
    # genuine deterministic gap. Project and addressed-skill caps match Step 3.5.
    projects: list[SuggestedProject] = []
    for candidate in llm_result.get("suggested_projects", [])[:3]:
        if not isinstance(candidate, dict):
            continue

        valid_addressed = [
            skill
            for skill in candidate.get("skills_addressed", [])
            if isinstance(skill, str) and skill.lower() in valid_gap_skills
        ][:5]

        projects.append(
            SuggestedProject(
                project_type=candidate.get("project_type", "Project"),
                description=candidate.get("description", ""),
                skills_addressed=valid_addressed,
            )
        )

    return missing, projects
