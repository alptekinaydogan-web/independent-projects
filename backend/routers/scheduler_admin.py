"""Admin — system health & maintenance endpoints.

Combines two utilities behind the same `/admin` prefix:
  - GET  /admin/system/health  → live operational vitals
  - POST /admin/demo/seed      → owner-only reseed of the demo dataset
"""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core import db, RESEND_API_KEY, RESEND_FROM_EMAIL
from security import require_admin, require_owner
from background_tasks import outstanding_count
from demo_seed import seed_demo_environment
from audit_helper import audit

router = APIRouter(prefix="/admin", tags=["scheduler"])

_BOOT_TS = time.time()


@router.get("/system/health")
async def system_health(_: dict = Depends(require_admin)):
    """Live operational vitals — DB reachability, background workload,
    and email delivery configuration."""
    db_ok = True
    db_latency_ms = None
    try:
        t0 = time.perf_counter()
        await db.command("ping")
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception:
        db_ok = False

    counts = {}
    if db_ok:
        counts = {
            "users":         await db.users.count_documents({}),
            "categories":    await db.categories.count_documents({}),
            "tv_projects":   await db.tv_projects.count_documents({}),
            "partner_submissions": await db.tv_projects.count_documents({"source": "partner"}),
            "productions":   await db.productions.count_documents({}),
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
    }


@router.post("/demo/seed")
async def reseed_demo_environment(owner: dict = Depends(require_owner)):
    """Owner-only: wipe operational data and repopulate with a realistic
    Project Library fixture. Preserves users, categories and TV projects.
    Idempotent — safe to run repeatedly.
    """
    try:
        summary = await seed_demo_environment()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await audit(owner, "demo.seed", "system", "", summary)
    return summary
