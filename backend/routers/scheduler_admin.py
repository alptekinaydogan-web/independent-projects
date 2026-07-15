"""Admin — system health & maintenance endpoints.

Combines two utilities behind the same `/admin` prefix:
  - POST /admin/scheduler/run-campaign-reminders  → force the scheduler tick
  - GET  /admin/system/health                     → live operational vitals
"""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from core import db, CAMPAIGN_REMINDER_DAYS, PROPOSAL_ARCHIVE_DAYS, RESEND_API_KEY, RESEND_FROM_EMAIL
from security import require_admin
from scheduler import run_once
from background_tasks import outstanding_count

router = APIRouter(prefix="/admin", tags=["scheduler"])

# Track boot time so uptime can be reported. Imported once at module load.
_BOOT_TS = time.time()


@router.post("/scheduler/run-campaign-reminders")
async def run_reminders_now(_: dict = Depends(require_admin)):
    await run_once()
    return {"ok": True}


@router.get("/system/health")
async def system_health(_: dict = Depends(require_admin)):
    """Live operational vitals — DB reachability, background workload,
    email delivery configuration and scheduler wiring."""
    # Ping Mongo — round-trip time in ms
    db_ok = True
    db_latency_ms = None
    try:
        t0 = time.perf_counter()
        await db.command("ping")
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception:
        db_ok = False

    # Cheap counts (indexed)
    counts = {}
    if db_ok:
        counts = {
            "users":         await db.users.count_documents({}),
            "campaigns":     await db.campaigns.count_documents({}),
            "sponsorships":  await db.sponsorships.count_documents({}),
            "tv_projects":   await db.tv_projects.count_documents({}),
            "audit_entries": await db.audit_log.count_documents({}),
            "notifications": await db.notifications.count_documents({}),
        }

    return {
        "status": "ok" if db_ok else "degraded",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - _BOOT_TS, 1),
        "database": {"ok": db_ok, "latency_ms": db_latency_ms, "counts": counts},
        "background_tasks": {
            "outstanding": outstanding_count(),
        },
        "email": {
            "provider": "resend",
            "configured": bool(RESEND_API_KEY),
            "from": RESEND_FROM_EMAIL if RESEND_API_KEY else None,
            "mode": "live" if RESEND_API_KEY else "dev-fallback",
        },
        "scheduler": {
            "campaign_reminder_days": CAMPAIGN_REMINDER_DAYS,
            "proposal_archive_days":  PROPOSAL_ARCHIVE_DAYS,
        },
    }
