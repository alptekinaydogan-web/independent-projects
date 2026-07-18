"""Admin: representatives CRUD + CRM profile.

Post-cleanup: statistics have been recentered on the Project Library.
Banner / TV sponsorship counters have been removed. Each representative
row now reports application activity (submitted / approved productions)
and partner project submissions instead.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso
from models import RepresentativeCreate, RepresentativeUpdate
from security import hash_password, require_admin
from audit_helper import audit
from notifications import notify

router = APIRouter(prefix="/admin/representatives", tags=["representatives"])


async def _rep_activity_stats(rep_id: str) -> dict:
    """Aggregate a rep's Project Library activity for the CRM index/profile."""
    submitted = 0
    approved = 0
    revision = 0
    rejected = 0
    last_activity = None
    async for a in db.productions.find({"rep_id": rep_id}):
        st = a.get("status", "submitted")
        if st == "submitted":
            submitted += 1
        elif st == "approved":
            approved += 1
        elif st == "revision_requested":
            revision += 1
        elif st == "rejected":
            rejected += 1
        for k in ("created_at", "decided_at"):
            v = a.get(k)
            if v and (last_activity is None or v > last_activity):
                last_activity = v
    partner_total = await db.proposals.count_documents({"rep_id": rep_id})
    partner_approved = await db.proposals.count_documents({"rep_id": rep_id, "status": "approved"})
    return {
        "applications_submitted": submitted,
        "applications_approved": approved,
        "applications_revision": revision,
        "applications_rejected": rejected,
        "applications_total": submitted + approved + revision + rejected,
        "partner_submissions_total": partner_total,
        "partner_submissions_approved": partner_approved,
        "last_activity_at": last_activity,
    }


@router.get("")
async def list_reps(_: dict = Depends(require_admin)):
    reps = await db.users.find({"role": "representative"}).to_list(500)
    for r in reps:
        r.pop("_id", None); r.pop("password_hash", None)
        r.update(await _rep_activity_stats(r["id"]))
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
        "country": body.country, "phone": body.phone or "",
        "website": body.website or "", "territory": body.territory or "",
        "is_active": body.is_active, "created_at": now_iso(),
        "approved_at": now_iso() if body.is_active else None,
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

    if activation_change:
        active = updates.get("is_active", True)
        await notify([rep_id],
                     event_type=("representative.reactivated" if active else "representative.suspended"),
                     title=("Your account was reactivated" if active
                            else "Your account was suspended"),
                     message=(f"An administrator restored full access to your Independent Projects account."
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
    """CRM-style profile aggregating every Project Library interaction for a rep."""
    rep = await db.users.find_one({"id": rep_id, "role": "representative"})
    if not rep:
        raise HTTPException(status_code=404, detail="Representative not found")
    rep.pop("_id", None); rep.pop("password_hash", None)

    stats = await _rep_activity_stats(rep_id)

    # Production applications (all statuses)
    applications = []
    async for a in db.productions.find({"rep_id": rep_id}).sort("created_at", -1).limit(50):
        a.pop("_id", None)
        applications.append(a)

    # Partner project submissions (new ideas)
    partner_submissions = []
    async for p in db.proposals.find({"rep_id": rep_id}).sort("created_at", -1).limit(50):
        p.pop("_id", None)
        partner_submissions.append(p)

    # Recent activity mix (last 30 combined)
    history = [
        {"kind": "application", "id": a["id"], "title": a.get("tv_project_title", ""),
         "status": a.get("status"), "created_at": a.get("created_at")}
        for a in applications
    ] + [
        {"kind": "partner_submission", "id": p["id"], "title": p.get("title", ""),
         "status": p.get("status"), "created_at": p.get("created_at")}
        for p in partner_submissions
    ]
    history.sort(key=lambda h: h.get("created_at") or "", reverse=True)
    history = history[:30]

    # Timeline — audit entries where the rep is either actor or entity
    timeline = []
    async for a in db.audit_log.find({"$or": [{"actor_id": rep_id}, {"entity_id": rep_id}]}).sort("created_at", -1).limit(80):
        a.pop("_id", None)
        timeline.append({"action": a.get("action"), "at": a.get("created_at"),
                          "actor_name": a.get("actor_name"), "actor_role": a.get("actor_role"),
                          "entity_type": a.get("entity_type"), "entity_id": a.get("entity_id"),
                          "details": a.get("details", {})})

    # Notifications sent to this rep
    notifications = []
    async for n in db.notifications.find({"user_id": rep_id}).sort("created_at", -1).limit(50):
        n.pop("_id", None)
        notifications.append(n)

    return {
        "representative": rep,
        "stats": stats,
        "applications": applications,
        "partner_submissions": partner_submissions,
        "history": history,
        "timeline": timeline,
        "notifications": notifications,
    }
