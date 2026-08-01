"""Dashboard notification and reminder diagnostics API."""

from fastapi import APIRouter, HTTPException, status

from app.models import SchedulerStatusResponse, TestReminderRequest, TestReminderResponse
from app.repositories import deadline_repository
from app.services.scheduler_service import (
    execute_reminder,
    list_scheduled_jobs,
    scheduler_is_running,
)


router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def scheduler_status() -> SchedulerStatusResponse:
    """Return process-local scheduler health and serializable jobs."""
    jobs = list_scheduled_jobs()
    return SchedulerStatusResponse(
        running=scheduler_is_running(),
        job_count=len(jobs),
        jobs=jobs,
    )


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
