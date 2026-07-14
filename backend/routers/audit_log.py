"""Read-only admin audit log."""
from typing import Optional
from fastapi import APIRouter, Depends, Query

from core import db
from security import require_admin

router = APIRouter(prefix="/admin/audit-log", tags=["audit"])


@router.get("")
async def get_audit_log(
    _: dict = Depends(require_admin),
    limit: int = Query(200, ge=1, le=1000),
    entity_type: Optional[str] = Query(None),
    actor_role: Optional[str] = Query(None),
):
    q: dict = {}
    if entity_type: q["entity_type"] = entity_type
    if actor_role: q["actor_role"] = actor_role
    items = await db.audit_log.find(q).sort("created_at", -1).to_list(limit)
    for i in items:
        i.pop("_id", None)
    return items
