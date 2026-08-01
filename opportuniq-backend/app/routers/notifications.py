"""Dashboard notification and reminder diagnostics API."""

from fastapi import APIRouter, HTTPException, status

from app.models import TestReminderRequest, TestReminderResponse
from app.repositories import deadline_repository
from app.services.scheduler_service import execute_reminder


router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.post("/test", response_model=TestReminderResponse)
async def test_reminder(payload: TestReminderRequest) -> TestReminderResponse:
    """Execute a reminder immediately without waiting for APScheduler."""
    deadline = await deadline_repository.get_deadline_by_id(payload.deadline_id)
    if deadline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deadline not found",
        )
    result = await execute_reminder(
        payload.deadline_id,
        deadline["profile_id"],
        reminder_offset="test",
        force=True,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test reminder could not be delivered.",
        )
    return TestReminderResponse(**result)
