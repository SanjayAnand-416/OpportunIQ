"""Check frontend API calls that depend on stable backend route shapes."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_API_ROOT = REPOSITORY_ROOT / "opportuniq-frontend" / "src" / "api"

EXPECTED_CALLS = {
    "profile.js": (
        "'/api/profile/upload'",
        "'/api/profile/manual'",
        "`/api/profile/${profileId}`",
    ),
    "opportunities.js": (
        "'/api/opportunities/search'",
        "'/api/opportunities'",
        "`/api/saved/${opportunityId}`",
    ),
    "gmail.js": (
        "'/api/gmail/status'",
        "'/api/gmail/scan'",
        "'/api/gmail/disconnect'",
    ),
    "gapAnalysis.js": (
        "`/api/gap-analysis/${profileId}`",
        "`/api/gap-analysis/analysis/${analysisId}`",
        "`/api/gap-analysis/${profileId}/for-opportunity/${opportunityId}`",
        "'/api/gap-analysis/run'",
    ),
}

EXPECTED_SOURCE = {
    "src/api/profile.js": (
        "formData.append('file', file)",
        "status === 503 && fallback === 'manual'",
        "AI resume extraction is currently unavailable.",
        "Resume extraction is taking longer than expected.",
        "We could not extract a profile from this resume.",
        "Unexpected server error. Please try again later.",
    ),
    "src/components/onboarding/ResumeUploadCard.jsx": (
        "onManualSetup",
        "Set Up Manually",
    ),
}


def validate() -> int:
    missing: list[str] = []
    for filename, calls in EXPECTED_CALLS.items():
        source = (FRONTEND_API_ROOT / filename).read_text(encoding="utf-8")
        missing.extend(
            f"{filename}: {call}" for call in calls if call not in source
        )
    frontend_root = FRONTEND_API_ROOT.parents[1]
    for relative_path, snippets in EXPECTED_SOURCE.items():
        source = (frontend_root / relative_path).read_text(encoding="utf-8")
        missing.extend(
            f"{relative_path}: {snippet}"
            for snippet in snippets
            if snippet not in source
        )
    if missing:
        raise SystemExit(f"Frontend contract calls are missing: {missing}")
    return sum(len(calls) for calls in EXPECTED_CALLS.values()) + sum(
        len(snippets) for snippets in EXPECTED_SOURCE.values()
    )


if __name__ == "__main__":
    call_count = validate()
    print(f"Frontend contract validation OK: {call_count} route calls checked")
