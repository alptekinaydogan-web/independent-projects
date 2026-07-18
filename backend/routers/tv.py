"""Independent Projects — the Project Library.

The Project Library is the sole commercial primitive in the platform.
Every project is a modular package composed of reusable content blocks
(hero, overview, audience, format, sponsorship, technical specs, brand
guidelines, download center, apply-to-produce). Country Partners
(representatives) discover projects and register their intention to
produce a specific project in their territory via the Apply-to-Produce
workflow. Administrators publish, freeze or reactivate projects and
review applications.

No pricing, no bidding, no banner marketplace — those have been
intentionally removed from the platform (see routers/campaigns.py and
routers/inventory.py in the git history for the deprecated model).
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, now_iso, ADMIN_ROLES, DEFAULT_CATEGORY_SLUG
from models import (TVProjectCreate, TVProjectUpdate, TVProjectStatusUpdate,
                    ApplyToProduceBody, ApplicationDecisionBody)
from security import get_current_user, require_admin, require_rep
from audit_helper import audit
from notifications import notify, notify_all_admins, notify_all_active_reps

router = APIRouter(tags=["projects"])


# ---------- Project catalog ----------
@router.get("/tv-projects")
async def list_tv_projects(user: dict = Depends(get_current_user),
                            status: Optional[str] = Query(None),
                            category_slug: Optional[str] = Query(None)):
    q: dict = {}
    if status:
        q["status"] = status
    elif user["role"] == "representative":
        q["status"] = "active"
    if category_slug:
        q["category_slug"] = category_slug
    items = await db.tv_projects.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
        # Application counts scoped for the caller
        pending = await db.productions.count_documents({"tv_project_id": i["id"], "status": "submitted"})
        approved = await db.productions.count_documents({"tv_project_id": i["id"], "status": "approved"})
        i["pending_applications_count"] = pending
        i["approved_applications_count"] = approved
        if user["role"] == "representative":
            mine = await db.productions.find_one({"tv_project_id": i["id"], "rep_id": user["id"]})
            i["my_application_status"] = mine.get("status") if mine else None
    return items


@router.get("/tv-projects/{project_id}")
async def get_tv_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    p.pop("_id", None)
    # For the rep, include their own application (if any) so the UI can render
    # the correct CTA (Apply / Submitted / Approved / Revision requested).
    if user["role"] == "representative":
        mine = await db.productions.find_one({"tv_project_id": project_id, "rep_id": user["id"]})
        if mine:
            mine.pop("_id", None)
            p["my_application"] = mine
    return p


# ---------- Apply to Produce ----------
@router.post("/tv-projects/{project_id}/apply")
async def apply_to_produce(project_id: str, body: ApplyToProduceBody,
                            user: dict = Depends(require_rep)):
    project = await db.tv_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("status") != "active":
        raise HTTPException(status_code=400, detail="This project is not open for new productions")
    existing = await db.productions.find_one({"tv_project_id": project_id, "rep_id": user["id"]})
    if existing:
        raise HTTPException(status_code=409, detail="You have already applied to produce this project")
    app_doc = {
        "id": str(uuid.uuid4()),
        "tv_project_id": project_id, "tv_project_title": project["title"],
        "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""), "country": user.get("country", ""),
        "message": body.message or "",
        "target_launch_date": body.target_launch_date or "",
        "status": "submitted",
        "representative_feedback": "",
        "internal_notes": "",
        "decided_at": "",
        "created_at": now_iso(),
    }
    await db.productions.insert_one(app_doc)
    await audit(user, "production.apply", "tv_project", project_id, {"application_id": app_doc["id"]})
    await notify_all_admins(
        event_type="production.applied",
        title=f"Production application · {project['title']}",
        message=f"{user.get('agency_name', user['name'])} ({user.get('country', '—')}) wants to produce this project in their territory.",
        entity_type="tv_project", entity_id=project_id,
        link="/admin/proposals-review",
        severity="action_required",
    )
    app_doc.pop("_id", None)
    return app_doc


@router.get("/tv-projects/{project_id}/applications")
async def list_project_applications(project_id: str,
                                     _: dict = Depends(require_admin)):
    apps = await db.productions.find({"tv_project_id": project_id}).sort("created_at", -1).to_list(200)
    for a in apps:
        a.pop("_id", None)
    return apps


@router.get("/my-productions")
async def my_productions(user: dict = Depends(require_rep)):
    apps = await db.productions.find({"rep_id": user["id"]}).sort("created_at", -1).to_list(200)
    for a in apps:
        a.pop("_id", None)
    return apps


@router.get("/productions")
async def list_all_applications(_: dict = Depends(require_admin),
                                 status: Optional[str] = Query(None)):
    """Admin view — every production application across every project."""
    q: dict = {}
    if status:
        q["status"] = status
    apps = await db.productions.find(q).sort("created_at", -1).to_list(500)
    for a in apps:
        a.pop("_id", None)
    return apps


APPLICATION_DECISIONS = {
    "approved":            {"title": "Your application to produce was approved",       "severity": "info"},
    "rejected":            {"title": "Your application to produce was not approved",   "severity": "info"},
    "revision_requested":  {"title": "Your application to produce needs revision",     "severity": "action_required"},
}


@router.patch("/productions/{application_id}/decision")
async def decide_application(application_id: str, body: ApplicationDecisionBody,
                              admin: dict = Depends(require_admin)):
    if body.decision not in APPLICATION_DECISIONS:
        raise HTTPException(status_code=400, detail="Invalid decision")
    doc = await db.productions.find_one({"id": application_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Application not found")
    if doc.get("status") == body.decision:
        doc.pop("_id", None)
        return doc

    updates = {
        "status": body.decision,
        "representative_feedback": (body.representative_feedback or "").strip(),
        "internal_notes": (body.internal_notes or "").strip(),
        "decided_at": now_iso(),
    }
    await db.productions.update_one({"id": application_id}, {"$set": updates})
    await audit(admin, f"production.{body.decision}", "tv_project", doc.get("tv_project_id", ""),
                {"application_id": application_id, "rep_id": doc.get("rep_id")})

    meta = APPLICATION_DECISIONS[body.decision]
    note = f" · {updates['representative_feedback']}" if updates["representative_feedback"] else ""
    await notify([doc["rep_id"]],
                 event_type=f"production.{body.decision}",
                 title=f"{meta['title']} · {doc.get('tv_project_title', '')}",
                 message=f"{meta['title']}.{note}",
                 entity_type="tv_project", entity_id=doc.get("tv_project_id", ""),
                 link=f"/rep/tv/{doc.get('tv_project_id', '')}",
                 severity=meta["severity"])

    updated = await db.productions.find_one({"id": application_id})
    updated.pop("_id", None)
    return updated


# ---------- Admin CRUD ----------
@router.post("/admin/tv-projects")
async def create_tv_project(body: TVProjectCreate, admin: dict = Depends(require_admin)):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = now_iso()
    # Keep both fields in sync until we fully retire the legacy `category` string
    doc["category_slug"] = doc.get("category_slug") or DEFAULT_CATEGORY_SLUG
    doc["category"] = doc["category_slug"]
    await db.tv_projects.insert_one(doc)
    await audit(admin, "tv_project.create", "tv_project", doc["id"],
                {"title": doc["title"], "status": doc.get("status")})
    if doc.get("status") == "active":
        await notify_all_active_reps(
            event_type="tv_project.launched",
            title=f"New project available in the Library · {doc['title']}",
            message=(f"{doc['total_episodes']} episodes ready for country partner production. "
                     "Open the project page to review the package and apply."),
            entity_type="tv_project", entity_id=doc["id"],
            link=f"/rep/tv/{doc['id']}",
            severity="info",
        )
    doc.pop("_id", None)
    return doc


@router.patch("/admin/tv-projects/{project_id}")
async def update_tv_project(project_id: str, body: TVProjectUpdate, admin: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "category_slug" in updates:
        updates["category"] = updates["category_slug"]  # legacy mirror
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
    await db.productions.delete_many({"tv_project_id": project_id})
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
    title = before.get("title", "Project")
    if body.status == "active":
        await notify_all_active_reps(
            event_type="tv_project.status.active",
            title=f"Project reopened · {title}",
            message="This project is open again for country partner production applications.",
            entity_type="tv_project", entity_id=project_id,
            link=f"/rep/tv/{project_id}", severity="info")
    elif body.status == "closed":
        rep_ids = await db.productions.distinct("rep_id",
                                                 {"tv_project_id": project_id, "status": "approved"})
        if rep_ids:
            await notify(rep_ids,
                         event_type="tv_project.status.closed",
                         title=f"Project frozen · {title}",
                         message="This project is closed to new production applications. Your approved production remains valid.",
                         entity_type="tv_project", entity_id=project_id,
                         link=f"/rep/tv/{project_id}", severity="info")
    return {"ok": True, "status": body.status}
