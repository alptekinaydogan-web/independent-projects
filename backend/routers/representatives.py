"""Admin: representatives CRUD."""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso
from models import RepresentativeCreate, RepresentativeUpdate
from security import hash_password, require_admin
from audit_helper import audit
from notifications import notify

router = APIRouter(prefix="/admin/representatives", tags=["representatives"])


@router.get("")
async def list_reps(_: dict = Depends(require_admin)):
    reps = await db.users.find({"role": "representative"}).to_list(500)
    for r in reps:
        r.pop("_id", None); r.pop("password_hash", None)
    return reps


@router.post("")
async def create_rep(body: RepresentativeCreate, admin: dict = Depends(require_admin)):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = {
        "id": str(uuid.uuid4()), "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name, "role": "representative", "agency_name": body.agency_name,
        "country": body.country, "is_active": body.is_active, "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    await audit(admin, "representative.create", "user", user["id"],
                {"email": user["email"], "agency_name": user["agency_name"]})
    user.pop("password_hash", None); user.pop("_id", None)
    return user


@router.patch("/{rep_id}")
async def update_rep(rep_id: str, body: RepresentativeUpdate, admin: dict = Depends(require_admin)):
    before = await db.users.find_one({"id": rep_id, "role": "representative"})
    if not before:
        raise HTTPException(status_code=404, detail="Representative not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    audit_details = {k: (v if k != "password" else "***") for k, v in updates.items()}
    password_reset = "password" in updates
    activation_change = "is_active" in updates and updates["is_active"] != before.get("is_active", True)

    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
    if updates:
        await db.users.update_one({"id": rep_id, "role": "representative"}, {"$set": updates})

    doc = await db.users.find_one({"id": rep_id})
    await audit(admin, "representative.update", "user", rep_id, audit_details)

    # Notifications — administrator actions affecting a representative
    if activation_change:
        active = updates.get("is_active", True)
        await notify([rep_id],
                     event_type=("representative.reactivated" if active else "representative.suspended"),
                     title=("Your account was reactivated" if active
                            else "Your account was suspended"),
                     message=(f"An administrator restored full access to your Independent Commerce account."
                              if active
                              else "An administrator temporarily suspended your access. Reach out to your platform owner to restore it."),
                     entity_type="user", entity_id=rep_id,
                     link="/rep",
                     severity=("info" if active else "action_required"))
    if password_reset:
        await notify([rep_id],
                     event_type="representative.password_reset",
                     title="Your password was reset by an administrator",
                     message="An administrator set a new password for your account. If you did not request this, contact the platform owner immediately.",
                     entity_type="user", entity_id=rep_id, link="/rep",
                     severity="info")

    doc.pop("_id", None); doc.pop("password_hash", None)
    return doc


@router.delete("/{rep_id}")
async def delete_rep(rep_id: str, admin: dict = Depends(require_admin)):
    res = await db.users.delete_one({"id": rep_id, "role": "representative"})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await audit(admin, "representative.delete", "user", rep_id, {})
    return {"ok": True}



@router.get("/{rep_id}/profile")
async def rep_profile(rep_id: str, _: dict = Depends(require_admin)):
    """Full CRM-style profile aggregating all commercial activity for a rep."""
    rep = await db.users.find_one({"id": rep_id, "role": "representative"})
    if not rep:
        raise HTTPException(status_code=404, detail="Representative not found")
    rep.pop("_id", None); rep.pop("password_hash", None)

    # Banner stats
    banner_by_status: dict = {}
    async for c in db.campaigns.find({"rep_id": rep_id}):
        banner_by_status[c.get("status", "unknown")] = banner_by_status.get(c.get("status", "unknown"), 0) + 1
    # TV stats
    tv_by_status: dict = {}
    async for s in db.sponsorships.find({"rep_id": rep_id}):
        tv_by_status[s.get("status", "unknown")] = tv_by_status.get(s.get("status", "unknown"), 0) + 1
    # Active campaigns (approved, non-archived, still within flight)
    active_campaigns = []
    from datetime import datetime as _dt, timezone as _tz
    today = _dt.now(_tz.utc).date().isoformat()
    async for c in db.campaigns.find({"rep_id": rep_id, "status": "approved", "is_archived": {"$ne": True}}):
        end = (c.get("end_date") or "")[:10]
        start = (c.get("start_date") or "")[:10]
        if not end or (start <= today <= end):
            c.pop("_id", None)
            active_campaigns.append({"id": c["id"], "campaign_name": c.get("campaign_name"),
                                      "network_name": c.get("network_name"), "position_name": c.get("position_name"),
                                      "start_date": start, "end_date": end, "offer_amount_usd": c.get("offer_amount_usd")})
    # Recent proposal history (last 30 mixed)
    history = []
    async for c in db.campaigns.find({"rep_id": rep_id}).sort("created_at", -1).limit(30):
        history.append({"kind": "banner", "id": c["id"], "title": c.get("campaign_name", ""),
                         "status": c.get("status"), "created_at": c.get("created_at"),
                         "amount": c.get("offer_amount_usd")})
    async for s in db.sponsorships.find({"rep_id": rep_id}).sort("created_at", -1).limit(30):
        history.append({"kind": "sponsorship", "id": s["id"], "title": s.get("proposal_name", ""),
                         "status": s.get("status"), "created_at": s.get("created_at"),
                         "amount": s.get("offer_amount_usd")})
    history.sort(key=lambda h: h.get("created_at") or "", reverse=True)
    history = history[:30]

    # Timeline — audit entries scoped to this rep as actor
    timeline = []
    async for a in db.audit_log.find({"actor_id": rep_id}).sort("created_at", -1).limit(50):
        a.pop("_id", None)
        timeline.append({"action": a.get("action"), "at": a.get("created_at"),
                          "entity_type": a.get("entity_type"), "entity_id": a.get("entity_id")})

    return {
        "representative": rep,
        "banner_stats": {"total": sum(banner_by_status.values()), **banner_by_status},
        "tv_stats": {"total": sum(tv_by_status.values()), **tv_by_status},
        "active_campaigns": active_campaigns,
        "history": history,
        "timeline": timeline,
    }
