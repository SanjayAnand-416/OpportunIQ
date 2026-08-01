"""Notification preference API."""

from fastapi import APIRouter, HTTPException, Query
from app.models import NotificationSettingsResponse, NotificationSettingsUpdate
from app.repositories import profile_repository, settings_repository

router = APIRouter(prefix="/api/settings", tags=["Settings"])


async def _require_profile(profile_id: str) -> str:
    clean = profile_id.strip()
    if not clean or await profile_repository.get_profile_by_id(clean) is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return clean


@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(profile_id: str = Query(...)):
    return await settings_repository.get_notification_settings(await _require_profile(profile_id))


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(payload: NotificationSettingsUpdate):
    profile_id = await _require_profile(payload.profile_id)
    updates = payload.model_dump(exclude_unset=True); updates.pop("profile_id", None)
    return await settings_repository.update_notification_settings(profile_id, updates)
