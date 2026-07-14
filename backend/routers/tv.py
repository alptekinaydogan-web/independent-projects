"""Independent TV projects + commercial sponsorship proposals.

Sponsorship proposals are negotiated: rep proposes an offer amount for one or
more episodes, admin approves / rejects / requests revision. No fixed price.
"""
import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, now_iso, ADMIN_ROLES
from models import TVProjectCreate, TVProjectUpdate, TVProjectStatusUpdate, TVProposalCreate, ProposalDecisionBody
from security import get_current_user, require_admin, require_rep
from audit_helper import audit
from notifications import notify, notify_all_admins, notify_all_active_reps

router = APIRouter(tags=["tv"])


# ---------- TV Projects ----------
@router.get("/tv-projects")
async def list_tv_projects(user: dict = Depends(get_current_user),
                            status: Optional[str] = Query(None)):
    q: dict = {}
    if status:
        q["status"] = status
    elif user["role"] == "representative":
        q["status"] = "active"
    items = await db.tv_projects.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
        # unique already-approved episodes (only approved sponsorships count)
        cur = db.sponsorships.find({"tv_project_id": i["id"], "status": "approved"})
        eps = set()
        async for s in cur:
            for e in s.get("episode_numbers", []):
                eps.add(e)
        i["sponsored_episodes"] = sorted(eps)
        # also count pending on this project for admin visibility
        pending = await db.sponsorships.count_documents({"tv_project_id": i["id"], "status": "pending_review"})
        i["pending_review_count"] = pending
    return items


@router.get("/tv-projects/{project_id}")
async def get_tv_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="TV project not found")
    p.pop("_id", None)
    cur = db.sponsorships.find({"tv_project_id": project_id, "status": "approved"})
    eps = []
    async for s in cur:
        for e in s.get("episode_numbers", []):
            eps.append({"episode": e, "sponsor_agency": s.get("agency_name", ""),
                        "client_reference": s.get("client_reference", "")})
    p["sponsored_episodes"] = eps
    return p


@router.post("/admin/tv-projects")
async def create_tv_project(body: TVProjectCreate, admin: dict = Depends(require_admin)):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = now_iso()
    await db.tv_projects.insert_one(doc)
    await audit(admin, "tv_project.create", "tv_project", doc["id"],
                {"title": doc["title"], "status": doc.get("status")})
    if doc.get("status") == "active":
        await notify_all_active_reps(
            event_type="tv_project.launched",
            title=f"New Independent TV production available · {doc['title']}",
            message=(f"{doc['total_episodes']} episodes available for sponsorship. "
                     "Open the catalog to review the investment page and submit a commercial proposal."),
            entity_type="tv_project", entity_id=doc["id"],
            link=f"/rep/tv/{doc['id']}",
            severity="info",
        )
    doc.pop("_id", None)
    return doc


@router.patch("/admin/tv-projects/{project_id}")
async def update_tv_project(project_id: str, body: TVProjectUpdate, admin: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.tv_projects.update_one({"id": project_id}, {"$set": updates})
    doc = await db.tv_projects.find_one({"id": project_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    await audit(admin, "tv_project.update", "tv_project", project_id, updates)
    doc.pop("_id", None)
    return doc


@router.delete("/admin/tv-projects/{project_id}")
async def delete_tv_project(project_id: str, admin: dict = Depends(require_admin)):
    res = await db.tv_projects.delete_one({"id": project_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit(admin, "tv_project.delete", "tv_project", project_id, {})
    return {"ok": True}


@router.patch("/admin/tv-projects/{project_id}/status")
async def set_tv_project_status(project_id: str, body: TVProjectStatusUpdate,
                                 admin: dict = Depends(require_admin)):
    if body.status not in ("active", "draft", "closed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    before = await db.tv_projects.find_one({"id": project_id})
    if not before:
        raise HTTPException(status_code=404, detail="Not found")
    if before.get("status") == body.status:
        return {"ok": True, "status": body.status}
    await db.tv_projects.update_one({"id": project_id}, {"$set": {"status": body.status}})
    await audit(admin, f"tv_project.status.{body.status}", "tv_project", project_id,
                {"from": before.get("status")})
    title = before.get("title", "TV project")
    if body.status == "active":
        await notify_all_active_reps(
            event_type="tv_project.status.active",
            title=f"TV project reopened · {title}",
            message="Fresh episodes are available for commercial proposals.",
            entity_type="tv_project", entity_id=project_id,
            link=f"/rep/tv/{project_id}", severity="info")
    elif body.status == "closed":
        sponsor_ids = await db.sponsorships.distinct("rep_id",
                                                      {"tv_project_id": project_id, "status": "approved"})
        if sponsor_ids:
            await notify(sponsor_ids,
                         event_type="tv_project.status.closed",
                         title=f"TV project frozen · {title}",
                         message="This production is closed to new proposals. Your existing approved sponsorships remain valid.",
                         entity_type="tv_project", entity_id=project_id,
                         link=f"/rep/tv/{project_id}", severity="info")
    return {"ok": True, "status": body.status}


# ---------- Sponsorship proposals ----------
@router.get("/sponsorships")
async def list_sponsorships(user: dict = Depends(get_current_user)):
    q = {} if user["role"] in ADMIN_ROLES else {"rep_id": user["id"]}
    items = await db.sponsorships.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items


@router.post("/sponsorships")
async def create_sponsorship_proposal(body: TVProposalCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives submit proposals")
    project = await db.tv_projects.find_one({"id": body.tv_project_id})
    if not project:
        raise HTTPException(status_code=404, detail="TV project not found")
    if project.get("status") != "active":
        raise HTTPException(status_code=400, detail="TV project is not open for new proposals")
    if body.offer_amount_usd <= 0:
        raise HTTPException(status_code=400, detail="Offer amount must be greater than zero")

    # Only approved sponsorships block an episode. Pending proposals may compete
    # for the same episode; admin picks which one to approve.
    taken = set()
    async for s in db.sponsorships.find({"tv_project_id": body.tv_project_id, "status": "approved"}):
        for e in s.get("episode_numbers", []):
            taken.add(e)
    for e in body.episode_numbers:
        if e in taken:
            raise HTTPException(status_code=409, detail=f"Episode {e} is already sponsored")
        if e < 1 or e > project["total_episodes"]:
            raise HTTPException(status_code=400, detail=f"Invalid episode {e}")

    proposal = {
        "id": str(uuid.uuid4()),
        "kind": "sponsorship",
        "tv_project_id": body.tv_project_id, "tv_project_title": project["title"],
        "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "proposal_name": body.proposal_name,
        "client_reference": body.client_reference,
        "episode_numbers": sorted(body.episode_numbers),
        "episode_count": len(body.episode_numbers),
        "offer_amount_usd": float(body.offer_amount_usd),
        "notes": body.notes,
        "status": "pending_review",
        "admin_notes": "", "decided_at": "",
        "created_at": now_iso(),
    }
    await db.sponsorships.insert_one(proposal)

    await audit(user, "proposal.sponsorship.submitted", "sponsorship", proposal["id"], {
        "tv_project": project["title"], "episodes": proposal["episode_count"],
        "offer_amount_usd": proposal["offer_amount_usd"],
    })
    await notify_all_admins(
        event_type="sponsorship_proposal.submitted",
        title=f"New TV sponsorship proposal · {project['title']}",
        message=(f"{user.get('agency_name', user['name'])} proposed ${int(proposal['offer_amount_usd']):,} "
                 f"for {proposal['episode_count']} episode(s). Review and decide."),
        entity_type="sponsorship", entity_id=proposal["id"],
        link="/admin/proposals-review",
        severity="action_required",
    )

    proposal.pop("_id", None)
    return proposal


TV_DECISION_MAP = {
    "approved":            {"title": "Your TV sponsorship proposal was approved",     "severity": "info"},
    "rejected":            {"title": "Your TV sponsorship proposal was not approved", "severity": "info"},
    "revision_requested":  {"title": "Your TV sponsorship proposal needs revision",   "severity": "action_required"},
}


@router.patch("/sponsorships/{proposal_id}/decision")
async def decide_sponsorship_proposal(proposal_id: str, body: ProposalDecisionBody,
                                       admin: dict = Depends(require_admin)):
    if body.decision not in TV_DECISION_MAP:
        raise HTTPException(status_code=400, detail="Invalid decision")
    doc = await db.sponsorships.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.get("status") == body.decision:
        doc.pop("_id", None)
        return doc

    # When approving, ensure no other approved proposal has already taken these episodes
    if body.decision == "approved":
        taken = set()
        async for s in db.sponsorships.find(
            {"tv_project_id": doc["tv_project_id"], "status": "approved", "id": {"$ne": proposal_id}}
        ):
            for e in s.get("episode_numbers", []):
                taken.add(e)
        clash = [e for e in doc.get("episode_numbers", []) if e in taken]
        if clash:
            raise HTTPException(status_code=409, detail=f"Episodes already taken: {clash}")

    await db.sponsorships.update_one({"id": proposal_id},
                                      {"$set": {"status": body.decision,
                                                 "admin_notes": body.admin_notes or "",
                                                 "decided_at": now_iso()}})
    await audit(admin, f"proposal.sponsorship.{body.decision}", "sponsorship", proposal_id,
                {"admin_notes": body.admin_notes or ""})

    meta = TV_DECISION_MAP[body.decision]
    note = f" · Note: {body.admin_notes}" if body.admin_notes else ""
    await notify([doc["rep_id"]],
                 event_type=f"sponsorship_proposal.{body.decision}",
                 title=f"{meta['title']} · {doc.get('tv_project_title', '')}",
                 message=f"{meta['title']}.{note}",
                 entity_type="sponsorship", entity_id=proposal_id,
                 link="/rep/sponsorships",
                 severity=meta["severity"])

    updated = await db.sponsorships.find_one({"id": proposal_id})
    updated.pop("_id", None)
    return updated
