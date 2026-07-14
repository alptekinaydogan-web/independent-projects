"""TV project proposals: representative submits, admin decides."""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso, ADMIN_ROLES
from models import ProposalCreate, ProposalDecision
from security import get_current_user, require_admin, require_rep
from audit_helper import audit
from notifications import notify, notify_all_admins

router = APIRouter(tags=["proposals"])


@router.get("/proposals")
async def list_proposals(user: dict = Depends(get_current_user)):
    q = {} if user["role"] in ADMIN_ROLES else {"rep_id": user["id"]}
    items = await db.proposals.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items


@router.post("/proposals")
async def create_proposal(body: ProposalCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives can submit proposals")
    doc = body.model_dump()
    doc.update({
        "id": str(uuid.uuid4()), "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "status": "in_review", "admin_notes": "", "created_at": now_iso(),
    })
    await db.proposals.insert_one(doc)
    await audit(user, "proposal.create", "proposal", doc["id"],
                {"title": doc["title"], "format": doc["format"], "country": doc["country"]})

    await notify_all_admins(
        event_type="proposal.submitted",
        title=f"New TV proposal from {user.get('agency_name', user['name'])} · {doc['title']}",
        message=f"{doc['format'].replace('_', ' ').title()} — {doc['country']} · {doc['estimated_episodes']} episodes estimated.",
        entity_type="proposal", entity_id=doc["id"], link="/admin/proposals",
    )

    doc.pop("_id", None)
    return doc


DECISION_TITLE = {
    "approved": "Your TV proposal was approved",
    "rejected": "Your TV proposal was not approved",
    "in_review": "Your TV proposal requires revision",
}
DECISION_MSG = {
    "approved": "Great news — Independent TV will move it forward. The team will be in touch with next steps.",
    "rejected": "Independent TV has declined this concept for now.",
    "in_review": "The administrator has requested revisions before making a final decision.",
}
DECISION_SEVERITY = {
    "approved": "info",
    "rejected": "info",
    "in_review": "action_required",
}


@router.patch("/admin/proposals/{proposal_id}")
async def decide_proposal(proposal_id: str, body: ProposalDecision, admin: dict = Depends(require_admin)):
    if body.status not in ("approved", "rejected", "in_review"):
        raise HTTPException(status_code=400, detail="Invalid status")
    before = await db.proposals.find_one({"id": proposal_id})
    if not before:
        raise HTTPException(status_code=404, detail="Not found")

    await db.proposals.update_one({"id": proposal_id},
                                   {"$set": {"status": body.status,
                                              "admin_notes": body.admin_notes or "",
                                              "decided_at": now_iso()}})
    doc = await db.proposals.find_one({"id": proposal_id})
    await audit(admin, f"proposal.{body.status}", "proposal", proposal_id,
                {"admin_notes": body.admin_notes or ""})

    # Notify the rep who submitted the proposal
    if before.get("rep_id") and before.get("status") != body.status:
        note = f" · Note: {body.admin_notes}" if body.admin_notes else ""
        await notify([before["rep_id"]],
                     event_type=f"proposal.{body.status}",
                     title=f"{DECISION_TITLE[body.status]} · {before['title']}",
                     message=f"{DECISION_MSG[body.status]}{note}",
                     entity_type="proposal", entity_id=proposal_id, link="/rep/proposals",
                     severity=DECISION_SEVERITY[body.status])

    doc.pop("_id", None)
    return doc
