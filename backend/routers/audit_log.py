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
    action: Optional[str] = Query(None, description="Exact match, or trailing '*' for prefix search"),
):
    """List recent audit entries.

    Filters:
      - entity_type: exact match on `entity_type` (e.g. 'campaign', 'sponsorship')
      - actor_role: exact match on `actor_role` (e.g. 'admin', 'owner')
      - action: exact match, OR trailing '*' for prefix match (e.g. 'proposal.banner.*')
    """
    q: dict = {}
    if entity_type:
        q["entity_type"] = entity_type
    if actor_role:
        q["actor_role"] = actor_role
    if action:
        if action.endswith("*"):
            prefix = action[:-1]
            q["action"] = {"$regex": f"^{_escape_regex(prefix)}"}
        else:
            q["action"] = action
    items = await db.audit_log.find(q).sort("created_at", -1).to_list(limit)
    for i in items:
        i.pop("_id", None)
    return items


def _escape_regex(s: str) -> str:
    """Escape regex metacharacters so the prefix is interpreted literally."""
    import re
    return re.escape(s)
