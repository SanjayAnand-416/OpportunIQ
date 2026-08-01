"""Dashboard notification and reminder diagnostics API."""

from fastapi import APIRouter, HTTPException, Query, status

from app.models import SchedulerStatusResponse, TestReminderRequest, TestReminderResponse
from app.repositories import deadline_repository, notification_repository
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


@router.get("")
async def list_notifications(
    profile_id: str = Query(...),
    unread_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=100),
) -> dict:
    """List dashboard notifications for one public profile ID."""
    notifications = await notification_repository.list_notifications(
        profile_id=profile_id,
        unread_only=unread_only,
        limit=limit,
    )
    return {
        "notifications": notifications,
        "count": len(notifications),
        "profile_id": profile_id,
    }


@router.patch("/read-all")
async def mark_all_read(profile_id: str = Query(...)) -> dict:
    """Mark all notifications for one profile as read."""
    updated_count = await notification_repository.mark_all_notifications_read(
        profile_id
    )
    return {"success": True, "profile_id": profile_id, "updated_count": updated_count}


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str) -> dict:
    """Mark one notification as read."""
    notification = await notification_repository.mark_notification_read(notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"success": True, "notification": notification}


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
