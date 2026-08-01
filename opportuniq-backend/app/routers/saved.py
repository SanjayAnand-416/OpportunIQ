"""Saved opportunity tracker API."""

from fastapi import APIRouter, HTTPException, Query, status

from app.models import SavedOpportunityCreateResponse, SavedOpportunityDeleteResponse, SavedOpportunityListResponse, SavedOpportunityResponse, SavedOpportunityUpdate
from app.repositories import opportunity_repository, profile_repository, saved_repository


router = APIRouter(prefix="/api/saved", tags=["Saved Opportunities"])


async def _require_profile(profile_id: str) -> str:
    clean = profile_id.strip()
    if not clean or await profile_repository.get_profile_by_id(clean) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return clean


@router.post("/{opportunity_id}", response_model=SavedOpportunityCreateResponse, status_code=201)
async def save_opportunity(opportunity_id: str, profile_id: str = Query(...)):
    profile_id = await _require_profile(profile_id)
    if await opportunity_repository.get_opportunity_by_id(opportunity_id) is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    saved = await saved_repository.save_opportunity(profile_id=profile_id, opportunity_id=opportunity_id)
    return SavedOpportunityCreateResponse(saved_id=saved["saved_id"], saved=SavedOpportunityResponse(**saved))


@router.get("", response_model=SavedOpportunityListResponse)
async def list_saved(profile_id: str = Query(...), status_filter: str | None = Query(None, alias="status"), platform: str | None = Query(None), limit: int = Query(100, ge=1, le=200)):
    profile_id = await _require_profile(profile_id)
    try:
        rows = await saved_repository.list_saved_opportunities(profile_id, status=status_filter, platform=platform, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SavedOpportunityListResponse(saved=[SavedOpportunityResponse(**row) for row in rows], count=len(rows), profile_id=profile_id)


@router.patch("/{saved_id}", response_model=SavedOpportunityResponse)
async def update_saved(saved_id: str, payload: SavedOpportunityUpdate):
    try:
        saved = await saved_repository.update_saved_opportunity(saved_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if saved is None: raise HTTPException(status_code=404, detail="Saved opportunity not found")
    return SavedOpportunityResponse(**saved)


@router.delete("/{saved_id}", response_model=SavedOpportunityDeleteResponse)
async def delete_saved(saved_id: str):
    if not await saved_repository.delete_saved_opportunity(saved_id):
        raise HTTPException(status_code=404, detail="Saved opportunity not found")
    return SavedOpportunityDeleteResponse(success=True, saved_id=saved_id)
