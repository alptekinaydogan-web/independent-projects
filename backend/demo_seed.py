"""Demo environment seeder for the QA phase.

Post-cleanup: banner marketplace / sponsorship fixture data has been
removed. The demo dataset now covers the Project Library lifecycle
end-to-end — production applications across every status, partner
project submissions, notifications, and a natural audit trail.

Idempotent: running the seeder twice wipes the operational collections
(`productions`, `proposals`, `notifications`, `audit_log`) and rebuilds
from the same fixture list. Users, categories and TV projects are
preserved.
"""
import uuid
from datetime import datetime, timezone, timedelta

from core import db, now_iso, logger


DEMO_REP_EMAIL = "victor.laurent@parismedia.fr"


_NOW = None  # type: ignore


def _now() -> datetime:
    global _NOW
    if _NOW is None:
        _NOW = datetime.now(timezone.utc)
    return _NOW


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _days_ago(n: int) -> str:
    return _iso(_now() - timedelta(days=n))


def _months_ago(m: int, day_offset: int = 0) -> str:
    return _iso(_now() - timedelta(days=30 * m - day_offset))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# Applications: (status, tv_project_index, months_ago, message)
APPLICATION_SCENARIOS = [
    ("submitted", 0, 0, "Ready to open production in Paris with our documentary unit as of Q3."),
    ("submitted", 1, 0, "Local season for the French TV market — talks underway with two national broadcasters."),
    ("revision_requested", 2, 1, "We would like to align the delivery format with the French Q4 slot."),
    ("approved", 0, 2, "Approved. Season launches in October — production crew locked."),
    ("approved", 2, 3, "Approved. Broadcast deal signed with a Tier-1 French partner."),
    ("rejected", 1, 4, "Not viable in the current window — parking for 2027."),
]

# Partner project submissions: (status, title, format, months_ago, description)
PARTNER_SUBMISSIONS = [
    ("in_review", "Voices from the Alps", "documentary", 0,
      "A three-part documentary series chronicling the villages of the French Alps in the age of climate transition."),
    ("in_review", "Grand Prix Diaries", "interview_series", 0,
      "Behind-the-scenes interview series with the mechanics, engineers and drivers who make Formula 1 possible in Monaco."),
    ("approved", "Parisian Bakers", "travel", 3,
      "10-part travel series celebrating the artisan bakers who keep the Paris skyline breathing at 5am."),
    ("rejected", "Cryptomonnaie France", "investigation", 5,
      "Investigation of the French crypto ecosystem — deprioritised in favour of the 2027 slate."),
]

NOTIF_FIXTURES = [
    ("rep", "production.approved",
     "Your application to produce was approved · World of Girls",
     "Approved. The Independent Media Network team will be in touch this week to co-ordinate the production kickoff.",
     "tv_project", "info", False, 2),
    ("rep", "production.revision_requested",
     "Your application to produce needs revision · Silent Continents",
     "Please align the delivery format with the French Q4 broadcast slot before we can approve.",
     "tv_project", "action_required", False, 12),
    ("rep", "tv_project.launched",
     "New project available in the Library · Silent Continents",
     "12 cinematic episodes now open for country partner production. Open the project page to review the modular package.",
     "tv_project", "info", True, 45),
    ("admin", "production.applied",
     "Production application · World of Girls",
     "Paris Media Group wants to produce this project in France.",
     "tv_project", "action_required", False, 1),
    ("admin", "proposal.submitted",
     "New project submission · Voices from the Alps",
     "Paris Media Group has submitted a new project idea for review.",
     "proposal", "action_required", False, 1),
]


async def _wipe() -> dict:
    counts = {
        "productions":   (await db.productions.delete_many({})).deleted_count,
        # Wipe only partner submissions (source=partner); official (admin) projects remain intact.
        "proposals":     (await db.tv_projects.delete_many({"source": "partner"})).deleted_count,
        "notifications": (await db.notifications.delete_many({})).deleted_count,
        "audit_log":     (await db.audit_log.delete_many({})).deleted_count,
    }
    # Also nuke the legacy `proposals` collection if it still exists (post-migration)
    if "proposals" in await db.list_collection_names():
        await db.proposals.drop()
    return counts


async def _get_actors():
    owner = await db.users.find_one({"role": "owner"})
    rep = await db.users.find_one({"email": DEMO_REP_EMAIL})
    return owner, rep


async def _tv_projects_list():
    projects = []
    async for p in db.tv_projects.find({"source": {"$ne": "partner"}}).sort("created_at", 1):
        p.pop("_id", None)
        projects.append(p)
    return projects


async def _write_audit(actor: dict, action: str, entity_type: str, entity_id: str,
                        when: str, details: dict | None = None) -> None:
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
        "created_at": when,
    })


async def seed_demo_environment() -> dict:
    """Wipe demo-scope data and repopulate with a workflow-complete fixture."""
    global _NOW
    _NOW = datetime.now(timezone.utc)

    owner, rep = await _get_actors()
    if not owner or not rep:
        raise RuntimeError("Demo seed requires the base seeder to have created the owner + rep users first.")

    wipe_counts = await _wipe()
    tv_projects = await _tv_projects_list()
    if not tv_projects:
        raise RuntimeError("Demo seed requires TV projects. Restart backend to run base seeder.")

    # -------- Applications --------
    application_docs = []
    for status, tv_idx, months_ago, message in APPLICATION_SCENARIOS:
        tv = tv_projects[tv_idx % len(tv_projects)]
        submitted_at = _months_ago(months_ago, day_offset=1)
        decided_at = ""
        rep_feedback = ""
        if status in ("approved", "rejected", "revision_requested"):
            decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=3))
            rep_feedback = {
                "approved": "Approved. Local production green-lit.",
                "rejected": "Not viable in the current window.",
                "revision_requested": "Please align delivery format with the current Q4 slot.",
            }.get(status, "")
        doc = {
            "id": str(uuid.uuid4()),
            "tv_project_id": tv["id"], "tv_project_title": tv["title"],
            "rep_id": rep["id"], "rep_name": rep["name"],
            "agency_name": rep.get("agency_name", ""), "country": rep.get("country", ""),
            "message": message,
            "target_launch_date": (_now() + timedelta(days=90)).date().isoformat(),
            "status": status,
            "representative_feedback": rep_feedback,
            "internal_notes": "" if status == "submitted" else "Reviewed by network committee",
            "decided_at": decided_at,
            "created_at": submitted_at,
        }
        application_docs.append(doc)
        await _write_audit(rep, "production.apply", "tv_project", tv["id"], submitted_at,
                           {"application_id": doc["id"]})
        if decided_at:
            await _write_audit(owner, f"production.{status}", "tv_project", tv["id"], decided_at,
                                {"application_id": doc["id"]})
    if application_docs:
        await db.productions.insert_many(application_docs)

    # -------- Partner submissions (unified into tv_projects) --------
    proposal_docs = []
    for status, title, fmt, months_ago, description in PARTNER_SUBMISSIONS:
        submitted_at = _months_ago(months_ago, day_offset=2)
        decided_at = ""
        admin_feedback = ""
        moderation = "submitted"
        published = False
        st = "draft"
        if status == "approved":
            moderation = "approved"
            published = True
            st = "active"
            decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=4))
            admin_feedback = "Approved — added to the 2026 slate."
        elif status == "rejected":
            moderation = "rejected"
            decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=4))
            admin_feedback = "Not viable — parked."
        elif status == "in_review":
            moderation = "submitted"
        doc = {
            "id": str(uuid.uuid4()),
            "title": title,
            "subtitle": "", "tagline": "",
            "overview": description, "synopsis": description,
            "concept": "",
            "production_format": fmt,
            "total_episodes": 10,
            "category_slug": "tv_formats", "category": "tv_formats",
            "status": st,
            "hero_image_url": "", "demo_video_url": "",
            "languages": [], "sponsorship_opportunities": [], "download_assets": [],
            "source": "partner",
            "moderation_status": moderation,
            "published": published, "featured": False, "archived": False,
            "admin_feedback": admin_feedback, "internal_notes": "",
            "revision_history": [],
            "submitted_by_rep_id": rep["id"],
            "submitted_by_rep_name": rep["name"],
            "submitted_by_agency": rep.get("agency_name", ""),
            "submitted_by_country": rep.get("country", ""),
            "submitted_at": submitted_at,
            "decided_at": decided_at,
            "created_at": submitted_at,
        }
        proposal_docs.append(doc)
        await _write_audit(rep, "proposal.create", "tv_project", doc["id"], submitted_at,
                           {"title": title, "format": fmt})
        if decided_at:
            await _write_audit(owner, f"proposal.{status}", "tv_project", doc["id"], decided_at,
                                {"admin_notes": admin_feedback})
    if proposal_docs:
        await db.tv_projects.insert_many(proposal_docs)

    # -------- Audit — light platform activity --------
    await _write_audit(owner, "tv_project.status.active", "tv_project", tv_projects[0]["id"],
                        _months_ago(4, 5), {"from": "draft"})
    await _write_audit(owner, "representative.create", "user", rep["id"],
                        _months_ago(6, 15), {"email": rep["email"], "agency": rep.get("agency_name")})

    # -------- Notifications --------
    admin_ids = [u["id"] async for u in db.users.find({"role": {"$in": ["owner", "admin"]}})]
    notif_docs = []
    for target, event_type, title, message, entity_type, severity, read, days_ago in NOTIF_FIXTURES:
        recipients = [rep["id"]] if target == "rep" else admin_ids
        for uid in recipients:
            notif_docs.append({
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "event_type": event_type,
                "title": title,
                "message": message,
                "entity_type": entity_type,
                "entity_id": "",
                "link": "/rep/tv" if target == "rep" else "/admin/proposals-review",
                "severity": severity,
                "read": read,
                "archived": False,
                "created_at": _days_ago(days_ago),
            })
    if notif_docs:
        await db.notifications.insert_many(notif_docs)

    summary = {
        "wiped": wipe_counts,
        "created": {
            "applications":         len(application_docs),
            "partner_submissions":  len(proposal_docs),
            "notifications":        len(notif_docs),
            "audit_entries":        len(application_docs) + len(proposal_docs) + 2,
        },
        "representative": rep["email"],
        "tv_projects_available": len(tv_projects),
        "generated_at": _iso(_now()),
    }
    logger.info(f"demo seed complete: {summary}")
    return summary
