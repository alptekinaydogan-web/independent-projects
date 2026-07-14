"""Admin: force scheduled jobs to run once (useful for testing)."""
from fastapi import APIRouter, Depends
from security import require_admin
from scheduler import run_once

router = APIRouter(prefix="/admin", tags=["scheduler"])


@router.post("/scheduler/run-campaign-reminders")
async def run_reminders_now(_: dict = Depends(require_admin)):
    await run_once()
    return {"ok": True}
