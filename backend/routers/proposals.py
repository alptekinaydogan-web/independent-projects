"""Legacy `/proposals` endpoints — now thin adapters over the unified
Project model.

Every partner submission is a document in `tv_projects` with
`source="partner"`. These endpoints reshape a Project document into the
legacy Proposal wire format so the older frontend calls keep working
during the migration to the unified `/projects` API.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso, DEFAULT_CATEGORY_SLUG, ADMIN_ROLES
from models import ProposalCreate, ProposalDecision
from security import get_current_user, require_admin, require_rep
from audit_helper import audit
from notifications import notify, notify_all_admins

router = APIRouter(tags=["proposals"])


def _to_wire(p: dict) -> dict:
    """Reshape a unified Project into the legacy Proposal wire format."""
    p = dict(p)  # local copy
    p.pop("_id", None)
    return {
        "id": p["id"],
        "title": p.get("title", ""),
        "format": p.get("production_format") or p.get("format") or "documentary",
        "country": p.get("submitted_by_country") or p.get("country") or "",
        "description": p.get("overview") or p.get("synopsis") or p.get("description") or "",
        "estimated_episodes": int(p.get("total_episodes") or p.get("estimated_episodes") or 0),
        "budget_hint_usd": float(p.get("budget_hint_usd") or 0),
        "rep_id": p.get("submitted_by_rep_id") or p.get("rep_id"),
        "rep_name": p.get("submitted_by_rep_name") or p.get("rep_name"),
        "agency_name": p.get("submitted_by_agency") or p.get("agency_name") or "",
        "status": _wire_status(p.get("moderation_status") or p.get("status")),
        "admin_notes": p.get("admin_feedback") or p.get("admin_notes") or "",
        "decided_at": p.get("decided_at") or "",
        "created_at": p.get("created_at") or "",
    }


def _wire_status(ms: str) -> str:
    """Map moderation_status to legacy proposal `status`."""
    if ms in ("approved", "rejected"):
        return ms
    if ms in ("draft", "submitted", "revision_requested", "in_review"):
        # Anything not decided appears "in_review" to the legacy consumers.
        return "in_review"
    return "in_review"


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
@router.get("/proposals")
async def list_proposals(user: dict = Depends(get_current_user)):
    q: dict = {"source": "partner"}
    if user["role"] not in ADMIN_ROLES:
        q["submitted_by_rep_id"] = user["id"]
    else:
        # Admins reviewing the inbox want everything except drafts
        q["moderation_status"] = {"$ne": "draft"}
    items = await db.tv_projects.find(q).sort("created_at", -1).to_list(500)
    return [_to_wire(i) for i in items]


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
@router.post("/proposals")
async def create_proposal(body: ProposalCreate, user: dict = Depends(require_rep)):
    """Legacy quick-submit endpoint — creates a unified Project with
    `source=partner`, `moderation_status=submitted` and maps the small
    proposal payload into the richer Project schema.
    """
    doc = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "subtitle": "",
        "tagline": "",
        "overview": body.description or "",
        "synopsis": body.description or "",
        "concept": "",
        "production_format": body.format or "documentary",
        "total_episodes": int(body.estimated_episodes or 0),
        "category_slug": DEFAULT_CATEGORY_SLUG,
        "category": DEFAULT_CATEGORY_SLUG,
        "status": "draft",
        "hero_image_url": "", "demo_video_url": "",
        "languages": [],
        "sponsorship_opportunities": [],
        "download_assets": [],
        # Partner submission metadata
        "source": "partner",
        "moderation_status": "submitted",
        "published": False, "featured": False, "archived": False,
        "admin_feedback": "", "internal_notes": "",
        "revision_history": [],
        "submitted_by_rep_id": user["id"],
        "submitted_by_rep_name": user["name"],
        "submitted_by_agency": user.get("agency_name", ""),
        "submitted_by_country": body.country or user.get("country", ""),
        "submitted_at": now_iso(),
        "decided_at": "",
        "created_at": now_iso(),
    }
    await db.tv_projects.insert_one(doc)
    await audit(user, "proposal.create", "tv_project", doc["id"],
                {"title": doc["title"], "format": doc["production_format"], "country": doc["submitted_by_country"]})

    await notify_all_admins(
        event_type="proposal.submitted",
        title=f"New project submission · {doc['title']}",
        message=f"{user.get('agency_name', user['name'])} has submitted a project for review.",
        entity_type="tv_project", entity_id=doc["id"],
        link=f"/admin/proposals?open={doc['id']}", severity="action_required")

    return _to_wire(doc)


# ---------------------------------------------------------------------------
# Legacy decision endpoint — forwards to unified moderation.
# ---------------------------------------------------------------------------
_LEGACY_TO_MODERATION = {
    "approved":   "approved",
    "rejected":   "rejected",
    "in_review":  "revision_requested",
}


@router.patch("/admin/proposals/{proposal_id}")
async def decide_proposal(proposal_id: str, body: ProposalDecision,
                           admin: dict = Depends(require_admin)):
    if body.status not in _LEGACY_TO_MODERATION:
        raise HTTPException(status_code=400, detail="Invalid status")
    p = await db.tv_projects.find_one({"id": proposal_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")

    decision = _LEGACY_TO_MODERATION[body.status]
    now = now_iso()
    updates = {
        "moderation_status": decision,
        "admin_feedback": (body.admin_notes or "").strip(),
        "decided_at": now,
    }
    if decision == "approved":
        updates["published"] = True
        if p.get("status") in (None, "draft"):
            updates["status"] = "active"

    history = {"at": now, "by": admin["id"], "by_name": admin.get("name"),
                "decision": decision, "admin_feedback": updates["admin_feedback"]}
    await db.tv_projects.update_one({"id": proposal_id},
                                     {"$set": updates, "$push": {"revision_history": history}})
    await audit(admin, f"proposal.{body.status}", "tv_project", proposal_id,
                {"admin_notes": updates["admin_feedback"]})

    submitter = p.get("submitted_by_rep_id")
    if submitter and p.get("moderation_status") != decision:
        titles = {
            "approved": "Your project was approved",
            "rejected": "Your project was declined",
            "revision_requested": "Your project needs revisions",
        }
        note = f" · Note: {updates['admin_feedback']}" if updates["admin_feedback"] else ""
        await notify([submitter],
                     event_type=f"proposal.{body.status}",
                     title=f"{titles[decision]} · {p.get('title', '')}",
                     message=f"{titles[decision]}.{note}",
                     entity_type="tv_project", entity_id=proposal_id,
                     link=f"/rep/projects/{proposal_id}",
                     severity="action_required" if decision == "revision_requested" else "info")

    doc = await db.tv_projects.find_one({"id": proposal_id})
    return _to_wire(doc)
