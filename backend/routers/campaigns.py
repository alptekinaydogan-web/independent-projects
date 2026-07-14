"""Banner commercial proposals — negotiated offer workflow.

Representatives submit a proposal for a standardized inventory product across the
Independent Media Network. Administrators approve, reject or request revision.
No fixed prices, no internal cost, no margin. The offer amount is what the rep
proposes to pay Independent Media Network for the placement.
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso, ADMIN_ROLES
from models import BannerProposalCreate, ProposalDecisionBody
from security import get_current_user, require_admin, require_rep
from audit_helper import audit
from notifications import notify, notify_all_admins
from networks_data import all_inventory

router = APIRouter(prefix="/campaigns", tags=["banner-proposals"])

_INV_INDEX = {i["id"]: i for i in all_inventory()}


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date() if "T" in s else datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _decorate(p: dict) -> dict:
    p.pop("_id", None)
    end = _parse_date(p.get("end_date"))
    start = _parse_date(p.get("start_date"))
    if p.get("status") == "approved" and end:
        today = datetime.now(timezone.utc).date()
        if today > end:
            p["lifecycle"] = "expired"
        elif start and today < start:
            p["lifecycle"] = "scheduled"
        else:
            p["lifecycle"] = "active"
        p["days_left"] = (end - today).days
    else:
        p["lifecycle"] = None
        p["days_left"] = None
    return p


@router.get("")
async def list_proposals(user: dict = Depends(get_current_user)):
    q = {} if user["role"] in ADMIN_ROLES else {"rep_id": user["id"]}
    items = await db.campaigns.find(q).sort("created_at", -1).to_list(500)
    return [_decorate(i) for i in items]


@router.post("")
async def create_banner_proposal(body: BannerProposalCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives submit commercial proposals")

    inv = _INV_INDEX.get(body.inventory_id)
    if not inv:
        raise HTTPException(status_code=400, detail="Unknown inventory item")

    start_date = body.start_date or datetime.now(timezone.utc).date().isoformat()
    end_date = body.end_date
    if end_date:
        sd = _parse_date(start_date); ed = _parse_date(end_date)
        if not sd or not ed:
            raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
        if ed < sd:
            raise HTTPException(status_code=400, detail="End date must be on or after start date")

    if body.offer_amount_usd <= 0:
        raise HTTPException(status_code=400, detail="Offer amount must be greater than zero")

    proposal = {
        "id": str(uuid.uuid4()),
        "kind": "banner",
        "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "campaign_name": body.proposal_name,
        "client_reference": body.client_reference,
        "inventory_id": body.inventory_id,
        "network_key": inv["network_key"], "network_name": inv["network_name"],
        "position_key": inv["position_key"], "position_name": inv["position_name"],
        "impressions": body.impressions,
        "start_date": start_date, "end_date": end_date or "",
        "offer_amount_usd": float(body.offer_amount_usd),
        "notes": body.notes,
        "status": "pending_review",
        "admin_notes": "", "decided_at": "",
        "created_at": now_iso(),
    }
    await db.campaigns.insert_one(proposal)

    await audit(user, "proposal.banner.submitted", "campaign", proposal["id"], {
        "network": inv["network_name"], "position": inv["position_name"],
        "offer_amount_usd": proposal["offer_amount_usd"],
    })
    await notify_all_admins(
        event_type="banner_proposal.submitted",
        title=f"New banner proposal · {proposal['campaign_name']}",
        message=(f"{user.get('agency_name', user['name'])} submitted a proposal for "
                 f"{inv['network_name']} · {inv['position_name']} at ${int(proposal['offer_amount_usd']):,}. "
                 "Review and approve, reject or request a revision."),
        entity_type="campaign", entity_id=proposal["id"],
        link="/admin/proposals-review",
        severity="action_required",
    )

    return _decorate(proposal)


DECISION_MAP = {
    "approved":            {"title": "Your banner proposal was approved",       "severity": "info"},
    "rejected":            {"title": "Your banner proposal was not approved",   "severity": "info"},
    "revision_requested":  {"title": "Your banner proposal needs revision",     "severity": "action_required"},
}


@router.patch("/{proposal_id}/decision")
async def decide_banner_proposal(proposal_id: str, body: ProposalDecisionBody,
                                  admin: dict = Depends(require_admin)):
    if body.decision not in DECISION_MAP:
        raise HTTPException(status_code=400, detail="Invalid decision")
    doc = await db.campaigns.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.get("status") == body.decision:
        return _decorate(doc)

    await db.campaigns.update_one({"id": proposal_id},
                                   {"$set": {"status": body.decision,
                                              "admin_notes": body.admin_notes or "",
                                              "decided_at": now_iso()}})
    await audit(admin, f"proposal.banner.{body.decision}", "campaign", proposal_id,
                {"admin_notes": body.admin_notes or ""})

    meta = DECISION_MAP[body.decision]
    note = f" · Note: {body.admin_notes}" if body.admin_notes else ""
    await notify([doc["rep_id"]],
                 event_type=f"banner_proposal.{body.decision}",
                 title=f"{meta['title']} · {doc['campaign_name']}",
                 message=f"{meta['title']}.{note}",
                 entity_type="campaign", entity_id=proposal_id,
                 link="/rep/banners",
                 severity=meta["severity"])

    updated = await db.campaigns.find_one({"id": proposal_id})
    return _decorate(updated)
