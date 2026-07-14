"""Notification center — helper to emit + router to consume."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from core import db, logger, now_iso, ADMIN_ROLES
from security import get_current_user
from models import MarkReadBody


# ---- Helper: emit ----
async def notify(user_ids: List[str], event_type: str, title: str, message: str,
                 entity_type: str = "", entity_id: str = "", link: str = "") -> None:
    """Create one notification per user_id."""
    if not user_ids:
        return
    docs = [{
        "id": str(uuid.uuid4()),
        "user_id": uid,
        "event_type": event_type,
        "title": title,
        "message": message,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "link": link,
        "read": False,
        "created_at": now_iso(),
    } for uid in user_ids]
    try:
        await db.notifications.insert_many(docs)
    except Exception as e:
        logger.error(f"notification insert failed ({event_type}): {e}")


async def notify_all_admins(event_type: str, title: str, message: str,
                             entity_type: str = "", entity_id: str = "", link: str = "") -> None:
    admins = await db.users.find({"role": {"$in": list(ADMIN_ROLES)}, "is_active": {"$ne": False}}).to_list(500)
    await notify([a["id"] for a in admins], event_type, title, message, entity_type, entity_id, link)


async def notify_all_active_reps(event_type: str, title: str, message: str,
                                  entity_type: str = "", entity_id: str = "", link: str = "") -> None:
    reps = await db.users.find({"role": "representative", "is_active": True}).to_list(500)
    await notify([r["id"] for r in reps], event_type, title, message, entity_type, entity_id, link)


# ---- Router ----
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user: dict = Depends(get_current_user),
                              limit: int = Query(50, ge=1, le=200),
                              unread_only: bool = Query(False)):
    q: dict = {"user_id": user["id"]}
    if unread_only:
        q["read"] = False
    items = await db.notifications.find(q).sort("created_at", -1).to_list(limit)
    for i in items:
        i.pop("_id", None)
    return items


@router.get("/unread-count")
async def unread_count(user: dict = Depends(get_current_user)):
    count = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    return {"count": count}


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    res = await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"read": True}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/mark-all-read")
async def mark_all_read(body: MarkReadBody, user: dict = Depends(get_current_user)):
    q: dict = {"user_id": user["id"], "read": False}
    if body.ids:
        q["id"] = {"$in": body.ids}
    res = await db.notifications.update_many(q, {"$set": {"read": True}})
    return {"ok": True, "updated": res.modified_count}
