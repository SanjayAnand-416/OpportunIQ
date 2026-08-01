"""Gap Advisor execution and persisted-result API."""

import asyncio
import importlib
import inspect
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.models import GapAnalysisResult, GapAnalysisRunRequest
from app.repositories import gap_analysis_repository
from app.repositories.opportunity_repository import get_opportunity_by_id
from app.repositories.profile_repository import get_profile_by_id
from app.websocket_manager import emit_trace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gap-analysis", tags=["Gap Analysis"])

async def _require_profile(profile_id: str):
    profile = await get_profile_by_id(profile_id)
    if profile is None: raise HTTPException(404, "Profile not found")
    return profile
async def _require_opportunity(opportunity_id: str):
    opportunity = await get_opportunity_by_id(opportunity_id)
    if opportunity is None: raise HTTPException(404, "Opportunity not found")
    return opportunity

def _load_gap_analysis_agent():
    for name in ("app.agents.gap_analysis_agent", "app.services.gap_analysis_service"):
        try: module = importlib.import_module(name)
        except ImportError: continue
        runner = getattr(module, "run", None)
        if callable(runner): return runner
    return None

async def _run_gap_analysis_agent(**kwargs) -> GapAnalysisResult:
    runner = _load_gap_analysis_agent()
    if runner is None: raise HTTPException(503, "Gap analysis service is not available.")
    parameters = inspect.signature(runner).parameters
    accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values())
    supported = kwargs if accepts_kwargs else {key: value for key, value in kwargs.items() if key in parameters}
    try:
        if inspect.iscoroutinefunction(runner): value = await asyncio.wait_for(runner(**supported), 60)
        else: value = await asyncio.wait_for(asyncio.to_thread(runner, **supported), 60)
    except TimeoutError as exc: raise HTTPException(504, "Gap analysis timed out.") from exc
    except ValueError as exc: raise HTTPException(422, "Gap analysis input was rejected.") from exc
    if hasattr(value, "model_dump"): value = value.model_dump()
    return GapAnalysisResult(**value)

def _guard_result(result: GapAnalysisResult, jd: str | None) -> GapAnalysisResult:
    data = result.model_dump()
    data["missing_skills"] = data["missing_skills"][:8]
    for skill in data["missing_skills"]:
        skill["learning_resources"] = [r for r in skill["learning_resources"] if str(r.get("url", "")).startswith(("http://", "https://"))][:5]
    data["suggested_projects"] = data["suggested_projects"][:3]
    data["jd_snippet"] = (jd or data.get("jd_snippet") or "")[:300] or None
    return GapAnalysisResult(**data)

@router.post("/run", response_model=GapAnalysisResult)
async def run_gap_analysis(payload: GapAnalysisRunRequest):
    await _require_profile(payload.profile_id)
    if payload.opportunity_id: await _require_opportunity(payload.opportunity_id)
    mode = "profile_vs_opportunity" if payload.opportunity_id else "profile_vs_jd" if payload.job_description else "profile_vs_role"
    session_id = payload.session_id or str(uuid.uuid4())
    await emit_trace(session_id, "gap-analysis", "running", "Loading student profile", {"analysis_mode": mode})
    try:
        result = await _run_gap_analysis_agent(profile_id=payload.profile_id, target_role=payload.target_role, job_description=payload.job_description, opportunity_id=payload.opportunity_id, session_id=session_id)
        if result.profile_id != payload.profile_id or result.analysis_mode != mode:
            raise HTTPException(502, "Gap analysis returned inconsistent identifiers.")
        result = _guard_result(result, payload.job_description)
        saved = await gap_analysis_repository.save_gap_analysis(result, persist=mode != "profile_vs_jd")
        response = GapAnalysisResult(**saved)
        await emit_trace(session_id, "gap-analysis", "complete", "Gap analysis complete", {"analysis_id": response.id, "analysis_mode": mode, "missing_skill_count": len(response.missing_skills)})
        return response
    except Exception as exc:
        try: await emit_trace(session_id, "gap-analysis", "error", "Gap analysis failed", {"analysis_mode": mode})
        except Exception: logger.warning("Could not emit gap-analysis error trace")
        raise exc

@router.get("/{profile_id}/for-opportunity/{opportunity_id}", response_model=GapAnalysisResult)
async def get_opportunity_gap_analysis(profile_id: str, opportunity_id: str):
    await _require_profile(profile_id); await _require_opportunity(opportunity_id)
    result = await gap_analysis_repository.get_opportunity_analysis(profile_id, opportunity_id)
    if result is None: raise HTTPException(404, "No gap analysis exists for this opportunity.")
    return GapAnalysisResult(**result)

@router.get("/{profile_id}", response_model=GapAnalysisResult)
async def get_latest_gap_analysis(profile_id: str):
    await _require_profile(profile_id)
    result = await gap_analysis_repository.get_latest_role_analysis(profile_id)
    if result is None: raise HTTPException(404, "No gap analysis found. Run POST /api/gap-analysis/run first.")
    return GapAnalysisResult(**result)
