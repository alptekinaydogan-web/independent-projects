"""Independent Projects — the unified Project Library.

Post-unification: administrator-created projects and country-partner
submissions share the exact same model. The distinction is expressed by
two fields:

  * `source`             — "admin" | "partner"
  * `moderation_status`  — "draft" | "submitted" | "revision_requested"
                            | "approved" | "rejected"

The `status` field remains a separate visibility flag (active | draft |
closed) used by administrators once a project has been approved. A
partner submission becomes an Official Project by simply flipping
`moderation_status` to "approved" and (optionally) `status` to "active".

Rep endpoints (`/projects/*`) are additive and coexist with the legacy
admin endpoints under `/admin/tv-projects/*` to keep the frontend
migration incremental.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, now_iso, ADMIN_ROLES, DEFAULT_CATEGORY_SLUG
from models import (TVProjectCreate, TVProjectUpdate, TVProjectStatusUpdate,
                    ApplyToProduceBody, ApplicationDecisionBody,
                    ProjectModerationBody, ProjectPublishBody,
                    ProjectFeatureBody, ProjectArchiveBody, ProjectAssetAdd)
from security import get_current_user, require_admin, require_rep
from audit_helper import audit
from notifications import notify, notify_all_admins, notify_all_active_reps

router = APIRouter(tags=["projects"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _project_defaults(source: str) -> dict:
    return {
        "source": source,
        "moderation_status": "approved" if source == "admin" else "draft",
        "published": source == "admin",
        "featured": False,
        "archived": False,
        "admin_feedback": "",
        "internal_notes": "",
        "revision_history": [],
        "submitted_at": "",
        "decided_at": "",
        "created_at": now_iso(),
    }


def _visible_to_rep(project: dict) -> bool:
    return (
        project.get("published") is True and
        project.get("archived") is not True and
        project.get("status") == "active" and
        project.get("moderation_status", "approved") == "approved"
    )


async def _augment(project: dict, user: dict) -> dict:
    project.pop("_id", None)
    pending = await db.productions.count_documents({"tv_project_id": project["id"], "status": "submitted"})
    approved = await db.productions.count_documents({"tv_project_id": project["id"], "status": "approved"})
    project["pending_applications_count"] = pending
    project["approved_applications_count"] = approved
    if user["role"] == "representative":
        mine = await db.productions.find_one({"tv_project_id": project["id"], "rep_id": user["id"]})
        project["my_application_status"] = mine.get("status") if mine else None
        if mine:
            mine.pop("_id", None)
            project["my_application"] = mine
    return project


def _can_edit(user: dict, project: dict) -> bool:
    if user["role"] in ADMIN_ROLES:
        return True
    if user["role"] != "representative":
        return False
    if project.get("submitted_by_rep_id") != user["id"]:
        return False
    return project.get("moderation_status") in ("draft", "revision_requested")


# ---------------------------------------------------------------------------
# Catalog (read)
# ---------------------------------------------------------------------------
@router.get("/tv-projects")
async def list_tv_projects(user: dict = Depends(get_current_user),
                            status: Optional[str] = Query(None),
                            category_slug: Optional[str] = Query(None),
                            source: Optional[str] = Query(None),
                            moderation_status: Optional[str] = Query(None)):
    q: dict = {}
    if user["role"] == "representative":
        # Country partners only see published + active + admin-approved projects.
        q["published"] = True
        q["archived"] = {"$ne": True}
        q["status"] = "active"
        q["moderation_status"] = "approved"
    else:
        if status:
            q["status"] = status
        if source:
            q["source"] = source
        if moderation_status:
            q["moderation_status"] = moderation_status
    if category_slug:
        q["category_slug"] = category_slug
    items = await db.tv_projects.find(q).sort([("featured", -1), ("created_at", -1)]).to_list(500)
    return [await _augment(i, user) for i in items]


@router.get("/tv-projects/{project_id}")
async def get_tv_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if user["role"] == "representative" and not _visible_to_rep(p):
        # Rep can still open their own draft/pending submission
        if p.get("submitted_by_rep_id") != user["id"]:
            raise HTTPException(status_code=404, detail="Project not found")
    return await _augment(p, user)


# ---------------------------------------------------------------------------
# Rep-owned project lifecycle (unified with admin)
# ---------------------------------------------------------------------------
@router.get("/my-projects")
async def my_projects(user: dict = Depends(require_rep)):
    items = await db.tv_projects.find({"submitted_by_rep_id": user["id"]}).sort("created_at", -1).to_list(200)
    return [await _augment(i, user) for i in items]


@router.post("/projects")
async def create_project(body: TVProjectCreate, user: dict = Depends(get_current_user)):
    """Create a new project draft.

    Reps create partner submissions (`source=partner`, `moderation_status=draft`,
    `published=false`). Admins create Official Projects directly
    (`source=admin`, `moderation_status=approved`, `published=true`).
    """
    is_admin = user["role"] in ADMIN_ROLES
    source = "admin" if is_admin else "partner"

    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc.update(_project_defaults(source))
    # Ensure list-typed fields are never null so $push operations succeed later
    for _lf in ("download_assets", "gallery", "languages",
                "sponsorship_opportunities", "key_selling_points"):
        if doc.get(_lf) is None:
            doc[_lf] = []
    doc["category_slug"] = doc.get("category_slug") or DEFAULT_CATEGORY_SLUG
    doc["category"] = doc["category_slug"]  # legacy mirror
    # Keep synopsis in sync with overview for the legacy detail view
    if doc.get("overview") and not doc.get("synopsis"):
        doc["synopsis"] = doc["overview"]
    if doc.get("synopsis") and not doc.get("overview"):
        doc["overview"] = doc["synopsis"]

    if not is_admin:
        doc["status"] = "draft"
        doc["published"] = False
        doc["submitted_by_rep_id"] = user["id"]
        doc["submitted_by_rep_name"] = user["name"]
        doc["submitted_by_agency"] = user.get("agency_name", "")
        doc["submitted_by_country"] = user.get("country", "")
    else:
        # Admin-created project publishes according to status; default active + published
        if doc.get("status") is None:
            doc["status"] = "active"

    await db.tv_projects.insert_one(doc)
    await audit(user, "project.create", "tv_project", doc["id"],
                {"title": doc["title"], "source": source, "status": doc.get("status")})

    if is_admin and doc.get("published") and doc.get("status") == "active":
        await notify_all_active_reps(
            event_type="tv_project.launched",
            title=f"New project available in the Library · {doc['title']}",
            message="Open the project page to review the modular package and apply to produce.",
            entity_type="tv_project", entity_id=doc["id"],
            link=f"/rep/tv/{doc['id']}", severity="info")

    return await _augment(doc, user)


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, body: TVProjectUpdate,
                          user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_edit(user, p):
        raise HTTPException(status_code=403, detail="You cannot edit this project right now")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "category_slug" in updates:
        updates["category"] = updates["category_slug"]
    # Keep overview/synopsis in sync so the legacy read-view keeps working
    if "overview" in updates and "synopsis" not in updates:
        updates["synopsis"] = updates["overview"]
    if "synopsis" in updates and "overview" not in updates:
        updates["overview"] = updates["synopsis"]
    if user["role"] not in ADMIN_ROLES:
        # Reps cannot change publication/moderation from an update payload
        for k in ("status", "published", "featured", "archived", "moderation_status"):
            updates.pop(k, None)
    if updates:
        updates["updated_at"] = now_iso()
        await db.tv_projects.update_one({"id": project_id}, {"$set": updates})
    doc = await db.tv_projects.find_one({"id": project_id})
    await audit(user, "project.update", "tv_project", project_id, {"keys": list(updates.keys())})
    return await _augment(doc, user)


@router.post("/projects/{project_id}/submit")
async def submit_project(project_id: str, user: dict = Depends(require_rep)):
    """Rep submits their draft (or revised draft) for admin moderation."""
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    if p.get("submitted_by_rep_id") != user["id"]:
        raise HTTPException(status_code=403, detail="This project isn't yours")
    if p.get("moderation_status") not in ("draft", "revision_requested"):
        raise HTTPException(status_code=400, detail="This project is not editable — it is already under review or decided.")
    if not p.get("title"):
        raise HTTPException(status_code=400, detail="A title is required before submission")

    updates = {"moderation_status": "submitted", "submitted_at": now_iso()}
    await db.tv_projects.update_one({"id": project_id}, {"$set": updates})
    await audit(user, "project.submit", "tv_project", project_id, {"title": p.get("title")})

    await notify_all_admins(
        event_type="proposal.submitted",
        title=f"New project submission · {p.get('title', '')}",
        message=f"{user.get('agency_name', user['name'])} has submitted a project for review.",
        entity_type="tv_project", entity_id=project_id,
        link=f"/admin/proposals?open={project_id}", severity="action_required")

    doc = await db.tv_projects.find_one({"id": project_id})
    return await _augment(doc, user)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    is_admin = user["role"] in ADMIN_ROLES
    if not is_admin:
        # Reps can only delete their own drafts
        if p.get("submitted_by_rep_id") != user["id"] or p.get("moderation_status") != "draft":
            raise HTTPException(status_code=403, detail="You cannot delete this project")
    await db.tv_projects.delete_one({"id": project_id})
    await db.productions.delete_many({"tv_project_id": project_id})
    await audit(user, "project.delete", "tv_project", project_id, {"title": p.get("title")})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin moderation & publication
# ---------------------------------------------------------------------------
MODERATION_DECISIONS = {
    "approved":            {"title": "Your project was approved",              "severity": "info"},
    "rejected":            {"title": "Your project was declined",              "severity": "info"},
    "revision_requested":  {"title": "Your project needs revisions",           "severity": "action_required"},
}


@router.patch("/admin/projects/{project_id}/moderate")
async def moderate_project(project_id: str, body: ProjectModerationBody,
                            admin: dict = Depends(require_admin)):
    if body.decision not in MODERATION_DECISIONS:
        raise HTTPException(status_code=400, detail="Invalid decision")
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")

    now = now_iso()
    updates = {
        "moderation_status": body.decision,
        "admin_feedback": (body.admin_feedback or "").strip(),
        "internal_notes": (body.internal_notes or "").strip(),
        "decided_at": now,
    }
    # Track revision history
    history_entry = {
        "at": now, "by": admin["id"], "by_name": admin.get("name"),
        "decision": body.decision, "admin_feedback": updates["admin_feedback"],
    }
    if body.decision == "approved":
        # Approved partner submission becomes an Official Project — go live
        updates["published"] = True
        if p.get("status") not in ("active", "draft", "closed"):
            updates["status"] = "active"
        elif p.get("status") == "draft":
            updates["status"] = "active"

    await db.tv_projects.update_one({"id": project_id},
                                     {"$set": updates,
                                      "$push": {"revision_history": history_entry}})
    await audit(admin, f"project.moderate.{body.decision}", "tv_project", project_id,
                {"admin_feedback": updates["admin_feedback"]})

    submitter = p.get("submitted_by_rep_id")
    if submitter:
        meta = MODERATION_DECISIONS[body.decision]
        note = f" · {updates['admin_feedback']}" if updates["admin_feedback"] else ""
        await notify([submitter],
                     event_type=f"proposal.{body.decision if body.decision != 'revision_requested' else 'in_review'}",
                     title=f"{meta['title']} · {p.get('title', '')}",
                     message=f"{meta['title']}.{note}",
                     entity_type="tv_project", entity_id=project_id,
                     link=f"/rep/projects/{project_id}",
                     severity=meta["severity"])

    if body.decision == "approved" and updates.get("published") and updates.get("status") == "active":
        await notify_all_active_reps(
            event_type="tv_project.launched",
            title=f"New project available in the Library · {p.get('title', '')}",
            message="A country-partner submission has been officially adopted by the network.",
            entity_type="tv_project", entity_id=project_id,
            link=f"/rep/tv/{project_id}", severity="info")

    doc = await db.tv_projects.find_one({"id": project_id})
    return await _augment(doc, admin)


@router.patch("/admin/projects/{project_id}/publish")
async def publish_project(project_id: str, body: ProjectPublishBody,
                           admin: dict = Depends(require_admin)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    await db.tv_projects.update_one({"id": project_id},
                                     {"$set": {"published": body.published}})
    await audit(admin, "project.publish" if body.published else "project.unpublish",
                "tv_project", project_id, {"published": body.published})
    doc = await db.tv_projects.find_one({"id": project_id})
    return await _augment(doc, admin)


@router.patch("/admin/projects/{project_id}/feature")
async def feature_project(project_id: str, body: ProjectFeatureBody,
                           admin: dict = Depends(require_admin)):
    if not await db.tv_projects.find_one({"id": project_id}):
        raise HTTPException(status_code=404, detail="Not found")
    await db.tv_projects.update_one({"id": project_id},
                                     {"$set": {"featured": body.featured}})
    await audit(admin, "project.feature" if body.featured else "project.unfeature",
                "tv_project", project_id, {"featured": body.featured})
    doc = await db.tv_projects.find_one({"id": project_id})
    return await _augment(doc, admin)


@router.patch("/admin/projects/{project_id}/archive")
async def archive_project(project_id: str, body: ProjectArchiveBody,
                           admin: dict = Depends(require_admin)):
    if not await db.tv_projects.find_one({"id": project_id}):
        raise HTTPException(status_code=404, detail="Not found")
    await db.tv_projects.update_one({"id": project_id},
                                     {"$set": {"archived": body.archived}})
    await audit(admin, "project.archive" if body.archived else "project.unarchive",
                "tv_project", project_id, {"archived": body.archived})
    doc = await db.tv_projects.find_one({"id": project_id})
    return await _augment(doc, admin)


# ---------------------------------------------------------------------------
# Download center — asset management
# ---------------------------------------------------------------------------
@router.post("/projects/{project_id}/assets")
async def add_asset(project_id: str, body: ProjectAssetAdd,
                     user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_edit(user, p):
        raise HTTPException(status_code=403, detail="You cannot edit this project")
    asset = {
        "id": str(uuid.uuid4()),
        "label": body.label,
        "url": body.url,
        "filetype": (body.filetype or "").lower(),
        "storage_path": body.storage_path or "",
        "original_filename": body.original_filename or "",
        "added_at": now_iso(),
    }
    await db.tv_projects.update_one({"id": project_id},
                                     {"$push": {"download_assets": asset}})
    await audit(user, "project.asset.add", "tv_project", project_id,
                {"label": body.label})
    return asset


@router.delete("/projects/{project_id}/assets/{asset_id}")
async def remove_asset(project_id: str, asset_id: str,
                        user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_edit(user, p):
        raise HTTPException(status_code=403, detail="You cannot edit this project")
    await db.tv_projects.update_one({"id": project_id},
                                     {"$pull": {"download_assets": {"id": asset_id}}})
    await audit(user, "project.asset.remove", "tv_project", project_id, {"asset_id": asset_id})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Apply-to-Produce workflow (unchanged from the previous iteration)
# ---------------------------------------------------------------------------
@router.post("/tv-projects/{project_id}/apply")
async def apply_to_produce(project_id: str, body: ApplyToProduceBody,
                            user: dict = Depends(require_rep)):
    project = await db.tv_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not _visible_to_rep(project):
        raise HTTPException(status_code=400, detail="This project is not open for new productions")
    existing = await db.productions.find_one({"tv_project_id": project_id, "rep_id": user["id"]})
    if existing:
        raise HTTPException(status_code=409, detail="You have already applied to produce this project")
    app_doc = {
        "id": str(uuid.uuid4()),
        "tv_project_id": project_id, "tv_project_title": project["title"],
        "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""), "country": user.get("country", ""),
        "message": body.message or "", "target_launch_date": body.target_launch_date or "",
        "status": "submitted",
        "representative_feedback": "", "internal_notes": "",
        "decided_at": "", "created_at": now_iso(),
    }
    await db.productions.insert_one(app_doc)
    await audit(user, "production.apply", "tv_project", project_id, {"application_id": app_doc["id"]})
    await notify_all_admins(
        event_type="production.applied",
        title=f"Production application · {project['title']}",
        message=f"{user.get('agency_name', user['name'])} ({user.get('country', '—')}) wants to produce this project in their territory.",
        entity_type="tv_project", entity_id=project_id,
        link="/admin/proposals-review", severity="action_required")
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
    q: dict = {"status": status} if status else {}
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
        doc.pop("_id", None); return doc

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


# ---------------------------------------------------------------------------
# Legacy admin endpoints kept alive as thin aliases so the older frontend
# routes continue to work while pages migrate to the unified /projects.
# ---------------------------------------------------------------------------
@router.post("/admin/tv-projects")
async def legacy_admin_create(body: TVProjectCreate, admin: dict = Depends(require_admin)):
    return await create_project(body, admin)


@router.patch("/admin/tv-projects/{project_id}")
async def legacy_admin_update(project_id: str, body: TVProjectUpdate,
                               admin: dict = Depends(require_admin)):
    return await update_project(project_id, body, admin)


@router.delete("/admin/tv-projects/{project_id}")
async def legacy_admin_delete(project_id: str, admin: dict = Depends(require_admin)):
    return await delete_project(project_id, admin)


@router.patch("/admin/tv-projects/{project_id}/status")
async def legacy_admin_status(project_id: str, body: TVProjectStatusUpdate,
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
    return {"ok": True, "status": body.status}
