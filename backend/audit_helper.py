"""Audit log helper — write a state-changing action to the audit_log collection."""
import uuid
from typing import Optional
from core import db, logger, now_iso


async def audit(actor: dict, action: str, entity_type: str, entity_id: str = "",
                details: Optional[dict] = None) -> None:
    try:
        await db.audit_log.insert_one({
            "id": str(uuid.uuid4()),
            "actor_id": actor.get("id"),
            "actor_email": actor.get("email"),
            "actor_name": actor.get("name"),
            "actor_role": actor.get("role"),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
            "created_at": now_iso(),
        })
    except Exception as e:
        logger.error(f"audit log write failed for {action}: {e}")
