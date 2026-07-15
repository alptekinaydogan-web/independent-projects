"""Demo environment seeder for the QA phase.

Populates the platform with a realistic, workflow-complete demo dataset:

  - One licensed representative (Victor Laurent · Paris Media Group)
  - Three Independent TV productions (already created by the base seeder)
  - Banner proposals covering EVERY lifecycle status
  - TV sponsorship proposals covering EVERY lifecycle status
  - Notification history for both the rep and administrators
  - Audit log entries written naturally as each proposal was recorded
  - Data timestamped across the last ~6 months so the reports view has a
    realistic trend line to display

Idempotent: running the demo seed twice wipes ALL non-user & non-inventory
records (`campaigns`, `sponsorships`, `notifications`, `audit_log`) and
rebuilds from the same fixture list, so QA can always reset to a known state.
Users, TV projects and the inventory catalog are preserved.
"""
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from core import db, now_iso, logger


DEMO_REP_EMAIL = "victor.laurent@parismedia.fr"


# ---------------------------------------------------------------------------
# Time helpers — evenly distribute data across the past N months
# ---------------------------------------------------------------------------
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


def _future(n: int) -> str:
    """A date `n` days from now, as a YYYY-MM-DD string (for banner start/end)."""
    return (_now() + timedelta(days=n)).date().isoformat()


def _date(iso: str) -> str:
    """Extract just the YYYY-MM-DD part of an ISO datetime."""
    return iso[:10]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
SAMPLE_CLIENTS = [
    ("SkyAero", "Airlines"),
    ("Verdance Hotels", "Hospitality"),
    ("Nordic Watches", "Luxury goods"),
    ("Meridian Bank", "Financial services"),
    ("Auréole Cosmetics", "Beauty"),
    ("VoltMotors", "Automotive"),
    ("Silva Tours", "Travel operator"),
    ("Helios Health", "Healthcare"),
    ("Praxis Real Estate", "Real estate"),
    ("Kite Tech", "Technology"),
    ("Fjord Outdoor", "Sportswear"),
    ("Golden Age Media", "Streaming"),
]


BANNER_SCENARIOS = [
    # status, inventory (network_key, position_key), campaign_name, client_idx, offer, impressions, months_ago
    ("pending_review", "global",       "hero",         "SkyAero — Global brand campaign Q2",         0,  18000, 320_000, 0),
    ("pending_review", "tourism",      "sidebar_top",  "Verdance Hotels — Summer takeover",           1,   9800, 180_000, 0),
    ("pending_review", "technology",   "header",       "Kite Tech — Product launch keynote",         9,  12500, 220_000, 0),

    ("revised",        "economy",      "hero",         "Meridian Bank — Wealth mandate 2026",         3,  27000, 400_000, 1),
    ("revised",        "tourism",      "hero",         "Silva Tours — Adventure package push",        6,   8400, 160_000, 1),

    ("revision_requested", "health",       "sidebar_top", "Helios Health — Preventive care awareness", 7,   6100, 120_000, 1),
    ("revision_requested", "sports",       "hero",        "Fjord Outdoor — Winter collection reveal", 10,  14200, 260_000, 2),

    ("approved",       "global",       "hero",         "Auréole Cosmetics — Global fragrance debut",  4,  32000, 520_000, 2),
    ("approved",       "tourism",      "header",       "Verdance Hotels — Fall bookings drive",        1,   9200, 190_000, 3),
    ("approved",       "economy",      "article_top",  "Meridian Bank — Institutional program",       3,  16800, 210_000, 3),
    ("approved",       "technology",   "hero",         "Kite Tech — Cloud platform expansion",         9,  22400, 340_000, 4),
    ("approved",       "sports",       "sidebar_top",  "Fjord Outdoor — Marathon partnership",        10,   7800, 145_000, 4),
    ("approved",       "real_estate",  "hero",         "Praxis Real Estate — International listings",  8,  19500, 265_000, 5),

    ("rejected",       "entertainment","hero",         "Golden Age Media — Streaming launch",         11,  36000, 480_000, 2),
    ("rejected",       "education",    "footer",       "Praxis Real Estate — Micro-listing sweep",     8,   1400,  45_000, 4),

    ("archived",       "global",       "hero",         "Auréole Cosmetics — Legacy 2025 sunset",       4,  28000, 450_000, 6),
    ("archived",       "tourism",      "hero",         "Silva Tours — Winter 2025 push (closed)",      6,   6800, 130_000, 6),
]

# Sponsorships: (status, tv_project_index, episodes, proposal_name, client_idx, offer, months_ago)
SPONSORSHIP_SCENARIOS = [
    ("pending_review", 0, [7, 8],          "SkyAero — Presenting sponsor · World of Girls",       0, 28000, 0),
    ("pending_review", 1, [3],             "Meridian Bank — Segment sponsor · Investigators",     3, 12000, 0),

    ("revised",        0, [23, 24, 25],    "Auréole Cosmetics — Season 1 revised block",          4, 42000, 1),
    ("revision_requested", 2, [2, 3],      "Verdance Hotels — Pair sponsorship · Silent",         1, 14000, 1),

    ("approved",       0, [11],            "Auréole Cosmetics — Episode 11 sponsorship",          4, 15200, 3),
    ("approved",       0, [30, 31, 32, 33],"SkyAero — Four-episode block",                        0, 48000, 4),
    ("approved",       1, [7],             "Meridian Bank — Episode 7 sponsorship",               3, 11500, 3),
    ("approved",       1, [12, 13],        "Nordic Watches — Two-episode block",                  2, 24000, 5),
    ("approved",       2, [5, 6],          "Verdance Hotels — Silent Continents sponsorship",     1, 21500, 4),

    ("rejected",       2, [1],             "VoltMotors — Silent Continents ep. 1 bid",            5,  4500, 2),
    ("archived",       0, [50, 51],        "Legacy 2025 · World of Girls block (closed)",         4, 28000, 6),
]


NOTIF_FIXTURES = [
    # For the rep
    ("rep", "banner_proposal.approved",
     "Your banner proposal was approved · Auréole Cosmetics — Global fragrance debut",
     "Approved at proposed terms. The signed PDF is on its way to your inbox.",
     "campaign", "info", False, 3),
    ("rep", "banner_proposal.revision_requested",
     "Your banner proposal needs revision · Helios Health — Preventive care awareness",
     "Please raise the impressions floor. Feedback: Increase to 200k monthly minimum.",
     "campaign", "action_required", False, 12),
    ("rep", "sponsorship_proposal.approved",
     "Your TV sponsorship proposal was approved · SkyAero — Four-episode block",
     "Approved. Delivery instructions and the signed PDF have been emailed.",
     "sponsorship", "info", True, 90),
    ("rep", "campaign.expiring.14d",
     "Banner campaign expiring in 14 days · Meridian Bank — Institutional program",
     "Your approved banner flight ends soon. Coordinate with your client on renewal.",
     "campaign", "reminder", False, 6),
    ("rep", "tv_project.launched",
     "New Independent TV production available · Silent Continents",
     "12 cinematic episodes now open for commercial proposals. Review the investment page.",
     "tv_project", "info", True, 45),
    # For admins (owner + admins)
    ("admin", "banner_proposal.submitted",
     "New banner proposal · SkyAero — Global brand campaign Q2",
     "Paris Media Group submitted a proposal at $18,000. Review and decide.",
     "campaign", "action_required", False, 1),
    ("admin", "sponsorship_proposal.submitted",
     "New TV sponsorship proposal · Meridian Bank — Segment sponsor · Investigators",
     "Paris Media Group proposed $12,000 for 1 episode. Review and decide.",
     "sponsorship", "action_required", False, 1),
    ("admin", "banner_proposal.revised",
     "Revised banner proposal · Meridian Bank — Wealth mandate 2026",
     "Paris Media Group resubmitted a revised proposal at $27,000. Review the updated offer.",
     "campaign", "action_required", False, 4),
]


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _hist(status: str, actor: dict, when: str,
           representative_feedback: str = "", internal_notes: str = "") -> dict:
    return {
        "status": status,
        "at": when,
        "actor_id": actor.get("id", ""),
        "actor_name": actor.get("name") or actor.get("email") or "system",
        "actor_role": actor.get("role", "system"),
        "representative_feedback": representative_feedback,
        "internal_notes": internal_notes,
    }


async def _wipe() -> dict:
    """Delete all commercial-side data while preserving users + inventory + TV projects."""
    counts = {
        "campaigns":     (await db.campaigns.delete_many({})).deleted_count,
        "sponsorships":  (await db.sponsorships.delete_many({})).deleted_count,
        "notifications": (await db.notifications.delete_many({})).deleted_count,
        "audit_log":     (await db.audit_log.delete_many({})).deleted_count,
        "proposals":     (await db.proposals.delete_many({})).deleted_count,  # editorial concepts
    }
    return counts


async def _get_actors():
    owner = await db.users.find_one({"role": "owner"})
    rep = await db.users.find_one({"email": DEMO_REP_EMAIL})
    return owner, rep


async def _inventory_index():
    from networks_data import all_inventory
    return {(i["network_key"], i["position_key"]): i for i in all_inventory()}


async def _tv_projects_list():
    projects = []
    async for p in db.tv_projects.find({}).sort("created_at", 1):
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


def _build_banner_lifecycle(*, status: str, inventory: dict, campaign_name: str,
                             client_ref: str, impressions: int, offer: float,
                             months_ago: int, owner: dict, rep: dict,
                             feedback_for_status: dict) -> dict:
    """Return a fully formed banner proposal dict with a coherent history array."""
    submitted_at = _months_ago(months_ago, day_offset=1)
    proposal_id = str(uuid.uuid4())
    history = [_hist("submitted", rep, submitted_at)]

    decided_at = ""
    is_archived = False
    archived_at = ""
    archived_by = ""
    parent = None

    if status in ("approved", "rejected"):
        decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=3))
        history.append(_hist(status, owner, decided_at,
                              representative_feedback=feedback_for_status.get(status, ""),
                              internal_notes=("CFO signed off · fully authorized" if status == "approved" else "Below floor; not viable at this rate")))
    elif status == "revision_requested":
        decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=2))
        history.append(_hist("revision_requested", owner, decided_at,
                              representative_feedback=feedback_for_status["revision_requested"],
                              internal_notes="Ask rep to raise floor by ~15%"))
    elif status == "revised":
        # This proposal represents the resubmission; create a synthetic parent id ref
        parent = str(uuid.uuid4())
        history[0] = _hist("revised", rep, submitted_at,
                            representative_feedback=f"Revision of proposal {parent[:8]}")
    elif status == "archived":
        decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=3))
        history.append(_hist("approved", owner, decided_at,
                              representative_feedback=feedback_for_status.get("approved", "Approved."),
                              internal_notes="Historic — 2025 season"))
        archived_at = _iso(datetime.fromisoformat(decided_at) + timedelta(days=95))
        archived_by = "system"
        is_archived = True
        history.append(_hist("archived", {"id": "system", "name": "System auto-archive", "role": "system"},
                              archived_at, internal_notes="Auto-archived after 90d retention"))
    # pending_review has just the submitted entry

    # Flight window
    if status == "approved":
        start_offset = -60 + months_ago * 5   # some already live, some scheduled
        start_date = _date(_iso(_now() + timedelta(days=start_offset)))
        end_date = _date(_iso(_now() + timedelta(days=start_offset + 60)))
    elif status == "archived":
        start_date = _date(_iso(_now() - timedelta(days=200)))
        end_date = _date(_iso(_now() - timedelta(days=140)))
    else:
        start_date = _future(30)
        end_date = _future(90)

    return {
        "id": proposal_id,
        "kind": "banner",
        "rep_id": rep["id"], "rep_name": rep["name"],
        "agency_name": rep.get("agency_name", ""),
        "campaign_name": campaign_name,
        "client_reference": client_ref,
        "inventory_id": inventory["id"],
        "network_key": inventory["network_key"], "network_name": inventory["network_name"],
        "position_key": inventory["position_key"], "position_name": inventory["position_name"],
        "impressions": impressions,
        "start_date": start_date, "end_date": end_date,
        "offer_amount_usd": float(offer),
        "notes": "Client eager to launch. Coverage priority: North America and Western Europe.",
        "status": ("pending_review" if status in ("pending_review",) else status),
        "representative_feedback": (history[-1]["representative_feedback"] if len(history) > 1 else ""),
        "internal_notes": (history[-1]["internal_notes"] if len(history) > 1 and history[-1].get("actor_role") in ("owner", "admin") else ""),
        "admin_notes": (history[-1]["representative_feedback"] if len(history) > 1 else ""),
        "decided_at": decided_at,
        "parent_proposal_id": parent,
        "is_archived": is_archived, "archived_at": archived_at, "archived_by": archived_by,
        "history": history,
        "created_at": submitted_at,
    }


def _build_sponsorship_lifecycle(*, status: str, tv_project: dict, episodes: list,
                                  proposal_name: str, client_ref: str, offer: float,
                                  months_ago: int, owner: dict, rep: dict,
                                  feedback_for_status: dict) -> dict:
    submitted_at = _months_ago(months_ago, day_offset=1)
    proposal_id = str(uuid.uuid4())
    history = [_hist("submitted", rep, submitted_at)]

    decided_at = ""
    is_archived = False
    archived_at = ""
    archived_by = ""
    parent = None

    if status in ("approved", "rejected"):
        decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=3))
        history.append(_hist(status, owner, decided_at,
                              representative_feedback=feedback_for_status.get(status, ""),
                              internal_notes=("Approved by network committee" if status == "approved" else "Slot conflicts with a higher-priority approval")))
    elif status == "revision_requested":
        decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=2))
        history.append(_hist("revision_requested", owner, decided_at,
                              representative_feedback=feedback_for_status["revision_requested"],
                              internal_notes="Consider expanding to two episodes for viability"))
    elif status == "revised":
        parent = str(uuid.uuid4())
        history[0] = _hist("revised", rep, submitted_at,
                            representative_feedback=f"Revision of proposal {parent[:8]}")
    elif status == "archived":
        decided_at = _iso(datetime.fromisoformat(submitted_at) + timedelta(days=3))
        history.append(_hist("approved", owner, decided_at,
                              representative_feedback="Approved.",
                              internal_notes="Historic — 2025 season"))
        archived_at = _iso(datetime.fromisoformat(decided_at) + timedelta(days=95))
        archived_by = "system"; is_archived = True
        history.append(_hist("archived", {"id": "system", "name": "System auto-archive", "role": "system"},
                              archived_at, internal_notes="Auto-archived after 90d retention"))

    return {
        "id": proposal_id,
        "kind": "sponsorship",
        "tv_project_id": tv_project["id"], "tv_project_title": tv_project["title"],
        "rep_id": rep["id"], "rep_name": rep["name"],
        "agency_name": rep.get("agency_name", ""),
        "proposal_name": proposal_name,
        "client_reference": client_ref,
        "episode_numbers": sorted(episodes),
        "episode_count": len(episodes),
        "offer_amount_usd": float(offer),
        "notes": "Presenting-sponsor tier requested. Client will provide creative assets 4 weeks pre-air.",
        "status": ("pending_review" if status in ("pending_review",) else status),
        "representative_feedback": (history[-1]["representative_feedback"] if len(history) > 1 else ""),
        "internal_notes": (history[-1]["internal_notes"] if len(history) > 1 and history[-1].get("actor_role") in ("owner", "admin") else ""),
        "admin_notes": (history[-1]["representative_feedback"] if len(history) > 1 else ""),
        "decided_at": decided_at,
        "parent_proposal_id": parent,
        "is_archived": is_archived, "archived_at": archived_at, "archived_by": archived_by,
        "history": history,
        "created_at": submitted_at,
    }


def _feedback_map() -> dict:
    return {
        "approved": "Approved at proposed terms. Signed PDF will be delivered to your inbox.",
        "rejected": "Not viable at this rate. Please revisit in Q4.",
        "revision_requested": "Increase the impressions floor by ~15% and resubmit.",
    }


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------
async def seed_demo_environment() -> dict:
    """Wipe non-user data and repopulate with a workflow-complete demo dataset.

    Returns a summary dict of what was created — useful for the admin UI toast.
    """
    global _NOW
    _NOW = datetime.now(timezone.utc)

    owner, rep = await _get_actors()
    if not owner or not rep:
        raise RuntimeError("Demo seed requires the base seeder to have created the owner + rep users first.")

    wipe_counts = await _wipe()
    inv_index = await _inventory_index()
    tv_projects = await _tv_projects_list()
    if len(tv_projects) < 3:
        raise RuntimeError("Demo seed requires at least three TV projects. Restart backend to run base seeder.")

    feedback = _feedback_map()

    # -------- Banners --------
    banner_docs = []
    banner_audits = []
    for status, net_key, pos_key, name, client_idx, offer, impressions, months_ago in BANNER_SCENARIOS:
        inv = inv_index.get((net_key, pos_key))
        if not inv:
            logger.warning(f"demo seed skipping unknown inventory {net_key}/{pos_key}")
            continue
        client, _ = SAMPLE_CLIENTS[client_idx]
        doc = _build_banner_lifecycle(status=status, inventory=inv, campaign_name=name,
                                       client_ref=client, impressions=impressions, offer=offer,
                                       months_ago=months_ago, owner=owner, rep=rep,
                                       feedback_for_status=feedback)
        banner_docs.append(doc)
        # Audit events matching the history transitions
        for entry in doc["history"]:
            actor = rep if entry["actor_role"] == "representative" else (owner if entry["actor_role"] in ("owner", "admin") else {"id": "system", "email": "system", "name": entry["actor_name"], "role": "system"})
            banner_audits.append({"actor": actor, "action": f"proposal.banner.{entry['status']}",
                                    "entity_id": doc["id"], "when": entry["at"],
                                    "details": {"network": doc["network_name"], "position": doc["position_name"],
                                                 "offer_amount_usd": doc["offer_amount_usd"]}})
    if banner_docs:
        await db.campaigns.insert_many(banner_docs)

    # -------- Sponsorships --------
    sponsor_docs = []
    sponsor_audits = []
    for status, tv_idx, episodes, name, client_idx, offer, months_ago in SPONSORSHIP_SCENARIOS:
        tv = tv_projects[tv_idx % len(tv_projects)]
        client, _ = SAMPLE_CLIENTS[client_idx]
        # Guard against episodes out of range
        max_ep = tv.get("total_episodes", 0)
        eps = [e for e in episodes if 1 <= e <= max_ep] or [1]
        doc = _build_sponsorship_lifecycle(status=status, tv_project=tv, episodes=eps,
                                            proposal_name=name, client_ref=client, offer=offer,
                                            months_ago=months_ago, owner=owner, rep=rep,
                                            feedback_for_status=feedback)
        sponsor_docs.append(doc)
        for entry in doc["history"]:
            actor = rep if entry["actor_role"] == "representative" else (owner if entry["actor_role"] in ("owner", "admin") else {"id": "system", "email": "system", "name": entry["actor_name"], "role": "system"})
            sponsor_audits.append({"actor": actor, "action": f"proposal.sponsorship.{entry['status']}",
                                     "entity_id": doc["id"], "when": entry["at"],
                                     "details": {"tv_project": tv["title"], "episodes": doc["episode_count"],
                                                  "offer_amount_usd": doc["offer_amount_usd"]}})
    if sponsor_docs:
        await db.sponsorships.insert_many(sponsor_docs)

    # -------- Audit log --------
    for a in banner_audits + sponsor_audits:
        await _write_audit(a["actor"], a["action"], "campaign" if "banner" in a["action"] else "sponsorship",
                            a["entity_id"], a["when"], a["details"])

    # Additional platform audits (project publishing, admin actions) — for realistic mix
    await _write_audit(owner, "tv_project.status.active", "tv_project", tv_projects[0]["id"],
                        _months_ago(4, 5), {"from": "draft"})
    await _write_audit(owner, "inventory.update", "banner_inventory", "global__hero",
                        _months_ago(5, 10), {"note": "Refreshed pricing model — proposal-based"})
    await _write_audit(owner, "representative.create", "user", rep["id"],
                        _months_ago(6, 15), {"email": rep["email"], "agency": rep.get("agency_name")})

    # -------- Notifications --------
    all_admin_ids = [u["id"] async for u in db.users.find({"role": {"$in": ["owner", "admin"]}})]
    notif_docs = []
    for target, event_type, title, message, entity_type, severity, read, days_ago in NOTIF_FIXTURES:
        recipients = [rep["id"]] if target == "rep" else all_admin_ids
        for uid in recipients:
            notif_docs.append({
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "event_type": event_type,
                "title": title,
                "message": message,
                "entity_type": entity_type,
                "entity_id": "",
                "link": "/rep/banners" if target == "rep" else "/admin/proposals-review",
                "severity": severity,
                "read": read,
                "archived": False,
                "created_at": _days_ago(days_ago),
            })
    if notif_docs:
        await db.notifications.insert_many(notif_docs)

    # -------- Summary --------
    summary = {
        "wiped": wipe_counts,
        "created": {
            "banner_proposals":       len(banner_docs),
            "sponsorship_proposals":  len(sponsor_docs),
            "notifications":          len(notif_docs),
            "audit_entries":          len(banner_audits) + len(sponsor_audits) + 3,
        },
        "representative": rep["email"],
        "tv_projects_available": len(tv_projects),
        "generated_at": _iso(_now()),
    }
    logger.info(f"demo seed complete: {summary}")
    return summary
