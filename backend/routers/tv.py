"""Independent TV projects + sponsorships router."""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from core import db, now_iso, ADMIN_ROLES
from models import TVProjectCreate, TVProjectUpdate, TVProjectStatusUpdate, SponsorshipCreate
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
        cur = db.sponsorships.find({"tv_project_id": i["id"]})
        eps = set()
        async for s in cur:
            for e in s.get("episode_numbers", []):
                eps.add(e)
        i["sponsored_episodes"] = sorted(eps)
    return items


@router.get("/tv-projects/{project_id}")
async def get_tv_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="TV project not found")
    p.pop("_id", None)
    cur = db.sponsorships.find({"tv_project_id": project_id})
    eps: dict = {}
    async for s in cur:
        for e in s.get("episode_numbers", []):
            eps[e] = {"episode": e, "sponsor_agency": s.get("agency_name", ""),
                      "client_name": s.get("client_name", "")}
    p["sponsored_episodes"] = list(eps.values())
    return p


@router.post("/admin/tv-projects")
async def create_tv_project(body: TVProjectCreate, admin: dict = Depends(require_admin)):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = now_iso()
    await db.tv_projects.insert_one(doc)
    await audit(admin, "tv_project.create", "tv_project", doc["id"],
                {"title": doc["title"], "status": doc.get("status")})

    # Broadcast new sponsorship opportunity when going live
    if doc.get("status") == "active":
        await notify_all_active_reps(
            event_type="tv_project.launched",
            title=f"New Independent TV production available · {doc['title']}",
            message=(f"{doc['total_episodes']} episodes · ${int(doc['price_per_episode_usd']):,}/ep internal. "
                     "Open the sponsorship catalog to review the investment page."),
            entity_type="tv_project", entity_id=doc["id"],
            link=f"/rep/tv/{doc['id']}",
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
            title=f"TV project reopened for sponsorship · {title}",
            message="Fresh episodes are available for sponsorship in the catalog.",
            entity_type="tv_project", entity_id=project_id,
            link=f"/rep/tv/{project_id}",
        )
    elif body.status == "closed":
        # notify the reps who already sponsored it
        sponsor_ids = await db.sponsorships.distinct("rep_id", {"tv_project_id": project_id})
        if sponsor_ids:
            await notify(sponsor_ids,
                         event_type="tv_project.status.closed",
                         title=f"TV project frozen · {title}",
                         message="This production has been closed to new sponsorships. Your existing sponsorships remain valid.",
                         entity_type="tv_project", entity_id=project_id,
                         link=f"/rep/tv/{project_id}")
    return {"ok": True, "status": body.status}


# ---------- Sponsorships ----------
@router.get("/sponsorships")
async def list_sponsorships(user: dict = Depends(get_current_user)):
    q = {} if user["role"] in ADMIN_ROLES else {"rep_id": user["id"]}
    items = await db.sponsorships.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items


@router.post("/sponsorships")
async def create_sponsorship(body: SponsorshipCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives can sponsor")
    project = await db.tv_projects.find_one({"id": body.tv_project_id})
    if not project:
        raise HTTPException(status_code=404, detail="TV project not found")
    if project.get("status") != "active":
        raise HTTPException(status_code=400, detail="TV project is not open for new sponsorships")

    cur = db.sponsorships.find({"tv_project_id": body.tv_project_id})
    taken = set()
    async for s in cur:
        for e in s.get("episode_numbers", []):
            taken.add(e)
    for e in body.episode_numbers:
        if e in taken:
            raise HTTPException(status_code=409, detail=f"Episode {e} already sponsored")
        if e < 1 or e > project["total_episodes"]:
            raise HTTPException(status_code=400, detail=f"Invalid episode {e}")

    internal_cost = round(project["price_per_episode_usd"] * len(body.episode_numbers), 2)
    sponsorship = {
        "id": str(uuid.uuid4()), "tv_project_id": body.tv_project_id,
        "tv_project_title": project["title"],
        "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "client_name": body.client_name,
        "episode_numbers": sorted(body.episode_numbers),
        "episode_count": len(body.episode_numbers),
        "internal_cost_usd": internal_cost,
        "client_total_price_usd": body.client_total_price,
        "margin_usd": round(body.client_total_price - internal_cost, 2),
        "notes": body.notes, "status": "confirmed",
        "created_at": now_iso(),
    }
    await db.sponsorships.insert_one(sponsorship)

    await audit(user, "sponsorship.create", "sponsorship", sponsorship["id"], {
        "tv_project_title": sponsorship["tv_project_title"],
        "client_name": sponsorship["client_name"],
        "episodes": sponsorship["episode_count"],
        "internal_cost_usd": sponsorship["internal_cost_usd"],
        "client_total_price_usd": sponsorship["client_total_price_usd"],
    })

    await notify_all_admins(
        event_type="sponsorship.created",
        title=f"New TV sponsorship confirmed · {sponsorship['tv_project_title']}",
        message=(f"{user.get('agency_name', user['name'])} sponsored {sponsorship['episode_count']} episode(s) "
                 f"for {sponsorship['client_name']} at ${int(sponsorship['client_total_price_usd']):,}."),
        entity_type="sponsorship", entity_id=sponsorship["id"],
        link=f"/admin/tv-projects/{project['id']}",
    )

    sponsorship.pop("_id", None)
    return sponsorship
