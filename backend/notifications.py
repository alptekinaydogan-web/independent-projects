"""Notification center — helper to emit + router to consume.

Categorization (severity):
  * action_required — the user MUST do something. Surface prominently in the
    dashboard "Needs your attention" strip.
  * reminder        — time-sensitive commercial nudge (e.g. campaign expiring).
  * info            — outcome or FYI (approved, activated, confirmed).

Notifications support soft-delete via `archived` — audit trail stays intact.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, logger, now_iso, ADMIN_ROLES
from security import get_current_user
from models import MarkReadBody

SEVERITIES = ("action_required", "reminder", "info")


# ---- Helper: emit ----
async def notify(user_ids: List[str], event_type: str, title: str, message: str,
                 entity_type: str = "", entity_id: str = "", link: str = "",
                 severity: str = "info") -> None:
    if not user_ids:
        return
    if severity not in SEVERITIES:
        severity = "info"
    docs = [{
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "event_type": event_type,
        "severity": severity,
        "title": title,
        "message": message,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "link": link,
        "read": False,
        "archived": False,
        "created_at": now_iso(),
    } for uid in user_ids]
    try:
        await db.notifications.insert_many(docs)
    except Exception as e:
        logger.error(f"notification insert failed ({event_type}): {e}")


async def notify_all_admins(event_type: str, title: str, message: str,
                             entity_type: str = "", entity_id: str = "", link: str = "",
                             severity: str = "info") -> None:
    admins = await db.users.find(
        {"role": {"$in": list(ADMIN_ROLES)}, "is_active": {"$ne": False}}
    ).to_list(500)
    await notify([a["id"] for a in admins], event_type, title, message,
                 entity_type, entity_id, link, severity)


async def notify_all_active_reps(event_type: str, title: str, message: str,
                                  entity_type: str = "", entity_id: str = "", link: str = "",
                                  severity: str = "info") -> None:
    reps = await db.users.find({"role": "representative", "is_active": True}).to_list(500)
    await notify([r["id"] for r in reps], event_type, title, message,
                 entity_type, entity_id, link, severity)


# ---- Router ----
router = APIRouter(prefix="/notifications", tags=["notifications"])


def _base_query(user_id: str, include_archived: bool) -> dict:
    q: dict = {"user_id": user_id}
    if not include_archived:
        q["archived"] = {"$ne": True}
    return q


@router.get("")
async def list_notifications(user: dict = Depends(get_current_user),
                              limit: int = Query(50, ge=1, le=500),
                              unread_only: bool = Query(False),
                              severity: Optional[str] = Query(None),
                              include_archived: bool = Query(False)):
    q = _base_query(user["id"], include_archived)
    if unread_only:
        q["read"] = False
    if severity in SEVERITIES:
        q["severity"] = severity
    items = await db.notifications.find(q).sort("created_at", -1).to_list(limit)
    for i in items:
        i.pop("_id", None)
    return items


@router.get("/unread-count")
async def unread_count(user: dict = Depends(get_current_user)):
    q = _base_query(user["id"], include_archived=False)
    q["read"] = False
    count = await db.notifications.count_documents(q)
    # Also break down by severity for badge
    pipeline = [{"$match": q}, {"$group": {"_id": "$severity", "n": {"$sum": 1}}}]
    by_sev = {"action_required": 0, "reminder": 0, "info": 0}
    async for doc in db.notifications.aggregate(pipeline):
        by_sev[doc["_id"]] = doc["n"]
    return {"count": count, "by_severity": by_sev}


@router.get("/actionable")
async def actionable(user: dict = Depends(get_current_user),
                      limit: int = Query(5, ge=1, le=20)):
    """Top unread action_required + reminder notifications, for dashboard strips."""
    q = _base_query(user["id"], include_archived=False)
    q["read"] = False
    q["severity"] = {"$in": ["action_required", "reminder"]}
    items = await db.notifications.find(q).sort("created_at", -1).to_list(limit)
    for i in items:
        i.pop("_id", None)
    return items


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    res = await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"read": True}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/{notification_id}/archive")
async def archive_one(notification_id: str, user: dict = Depends(get_current_user)):
    res = await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"archived": True, "read": True}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/mark-all-read")
async def mark_all_read(body: MarkReadBody, user: dict = Depends(get_current_user)):
    q = _base_query(user["id"], include_archived=False)
    q["read"] = False
    if body.ids:
        q["id"] = {"$in": body.ids}
    res = await db.notifications.update_many(q, {"$set": {"read": True}})
    return {"ok": True, "updated": res.modified_count}


@router.post("/archive-read")
async def archive_all_read(user: dict = Depends(get_current_user)):
    """Bulk soft-delete every notification the user has already read."""
    q = _base_query(user["id"], include_archived=False)
    q["read"] = True
    res = await db.notifications.update_many(q, {"$set": {"archived": True}})
    return {"ok": True, "archived": res.modified_count}
