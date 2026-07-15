"""Banner commercial proposals — negotiated offer workflow.

Representatives submit a proposal for a standardized inventory product across
the Independent Media Network. Administrators approve, reject, request revision,
or archive. No fixed prices, no internal cost, no margin. The offer amount is
what the rep proposes to pay Independent Media Network for the placement.

Full lifecycle:
    submitted (pending_review) → revision_requested → duplicate → revised
    → approved | rejected → archived
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso, ADMIN_ROLES, logger
from models import BannerProposalCreate, ProposalDecisionBody, ProposalArchiveBody, ProposalDuplicateOverrides
from security import get_current_user, require_admin, require_rep
from audit_helper import audit
from notifications import notify, notify_all_admins
from networks_data import all_inventory
from proposal_history import history_entry, strip_internal_notes, resolve_feedback
from proposal_pdf import generate_proposal_pdf
from email_service import send_approved_proposal_email
from fastapi.responses import StreamingResponse
import asyncio
import io

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


def _finalize(p: dict, user: dict) -> dict:
    """Decorate + strip internal notes for representatives."""
    p = _decorate(p)
    if user["role"] not in ADMIN_ROLES:
        p = strip_internal_notes(p)
    return p


async def _deliver_banner_approval_email(proposal: dict, admin: dict) -> None:
    """Background task: build the branded PDF and email it to the owning rep.

    Uses the rep-facing view of the proposal (internal notes stripped) so the
    document mirrors what the rep can share with their customer.
    """
    rep_id = proposal.get("rep_id")
    if not rep_id:
        return
    try:
        rep = await db.users.find_one({"id": rep_id})
        if not rep or not rep.get("email"):
            return
        rep_view = strip_internal_notes({k: v for k, v in proposal.items() if k != "_id"})
        pdf_bytes = generate_proposal_pdf(rep_view)
        ok = await send_approved_proposal_email(rep["email"], rep.get("name", ""),
                                                 "banner", rep_view, pdf_bytes)
        await audit(admin, "proposal.banner.pdf_emailed" if ok else "proposal.banner.pdf_email_failed",
                    "campaign", proposal["id"], {"to": rep["email"], "ok": ok,
                                                  "pdf_bytes": len(pdf_bytes)})
    except Exception as e:  # never let a background failure crash anything
        logger.error(f"[banner approval email] {proposal.get('id')}: {e}")


@router.get("")
async def list_proposals(user: dict = Depends(get_current_user),
                          include_archived: bool = False):
    q: dict = {} if user["role"] in ADMIN_ROLES else {"rep_id": user["id"]}
    if not include_archived:
        q["is_archived"] = {"$ne": True}
    items = await db.campaigns.find(q).sort("created_at", -1).to_list(500)
    return [_finalize(i, user) for i in items]


@router.get("/{proposal_id}")
async def get_proposal(proposal_id: str, user: dict = Depends(get_current_user)):
    doc = await db.campaigns.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if user["role"] not in ADMIN_ROLES and doc.get("rep_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _finalize(doc, user)


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
        "representative_feedback": "", "internal_notes": "",
        "admin_notes": "",  # legacy mirror
        "decided_at": "",
        "parent_proposal_id": None,
        "is_archived": False, "archived_at": "", "archived_by": "",
        "history": [history_entry("submitted", user)],
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

    return _finalize(proposal, user)


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
    if doc.get("is_archived"):
        raise HTTPException(status_code=400, detail="Proposal is archived")
    if doc.get("status") == body.decision:
        return _finalize(doc, admin)

    rep_feedback = resolve_feedback(body)
    internal = (body.internal_notes or "").strip()
    entry = history_entry(body.decision, admin,
                          representative_feedback=rep_feedback,
                          internal_notes=internal)

    await db.campaigns.update_one({"id": proposal_id},
                                   {"$set": {"status": body.decision,
                                              "representative_feedback": rep_feedback,
                                              "internal_notes": internal,
                                              "admin_notes": rep_feedback,  # legacy mirror
                                              "decided_at": now_iso()},
                                    "$push": {"history": entry}})
    await audit(admin, f"proposal.banner.{body.decision}", "campaign", proposal_id,
                {"representative_feedback": rep_feedback, "has_internal_notes": bool(internal)})

    meta = DECISION_MAP[body.decision]
    note = f" · Note: {rep_feedback}" if rep_feedback else ""
    await notify([doc["rep_id"]],
                 event_type=f"banner_proposal.{body.decision}",
                 title=f"{meta['title']} · {doc['campaign_name']}",
                 message=f"{meta['title']}.{note}",
                 entity_type="campaign", entity_id=proposal_id,
                 link="/rep/banners",
                 severity=meta["severity"])

    updated = await db.campaigns.find_one({"id": proposal_id})

    # On approval, deliver the branded proposal PDF to the owning rep.
    if body.decision == "approved":
        asyncio.create_task(_deliver_banner_approval_email(updated, admin))
    return _finalize(updated, admin)


@router.post("/{proposal_id}/duplicate")
async def duplicate_banner_proposal(proposal_id: str,
                                     body: ProposalDuplicateOverrides,
                                     user: dict = Depends(require_rep)):
    """Rep clones a proposal (typically after `revision_requested`) so they
    can adjust and resubmit without retyping. The new record is linked to the
    original via `parent_proposal_id`, starts life at status `revised`, and
    inherits every field from the parent that the rep did not override."""
    parent = await db.campaigns.find_one({"id": proposal_id})
    if not parent:
        raise HTTPException(status_code=404, detail="Original proposal not found")
    if parent.get("rep_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You can only duplicate your own proposals")

    # Inventory must still exist
    inv = _INV_INDEX.get(parent.get("inventory_id"))
    if not inv:
        raise HTTPException(status_code=400, detail="Original inventory product no longer available")

    def pick(over, fallback):
        return over if over is not None else fallback

    offer = pick(body.offer_amount_usd, parent.get("offer_amount_usd"))
    if not offer or float(offer) <= 0:
        raise HTTPException(status_code=400, detail="Offer amount must be greater than zero")

    start_date = pick(body.start_date, parent.get("start_date")) or datetime.now(timezone.utc).date().isoformat()
    end_date = pick(body.end_date, parent.get("end_date")) or ""
    if end_date:
        sd = _parse_date(start_date); ed = _parse_date(end_date)
        if not sd or not ed or ed < sd:
            raise HTTPException(status_code=400, detail="Invalid date range")

    proposal_name = pick(body.proposal_name, parent.get("campaign_name")) or "Revised proposal"
    client_ref = pick(body.client_reference, parent.get("client_reference")) or ""
    impressions = pick(body.impressions, parent.get("impressions"))
    notes = pick(body.notes, parent.get("notes"))

    new = {
        "id": str(uuid.uuid4()),
        "kind": "banner",
        "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "campaign_name": proposal_name,
        "client_reference": client_ref,
        "inventory_id": inv["id"],
        "network_key": inv["network_key"], "network_name": inv["network_name"],
        "position_key": inv["position_key"], "position_name": inv["position_name"],
        "impressions": impressions,
        "start_date": start_date, "end_date": end_date,
        "offer_amount_usd": float(offer),
        "notes": notes or "",
        "status": "revised",
        "representative_feedback": "", "internal_notes": "",
        "admin_notes": "",
        "decided_at": "",
        "parent_proposal_id": parent["id"],
        "is_archived": False, "archived_at": "", "archived_by": "",
        "history": [
            history_entry("revised", user,
                          representative_feedback=f"Revision of proposal {parent['id']}"),
        ],
        "created_at": now_iso(),
    }
    await db.campaigns.insert_one(new)

    await audit(user, "proposal.banner.revised", "campaign", new["id"], {
        "parent": parent["id"], "offer_amount_usd": new["offer_amount_usd"],
    })
    await notify_all_admins(
        event_type="banner_proposal.revised",
        title=f"Revised banner proposal · {new['campaign_name']}",
        message=(f"{user.get('agency_name', user['name'])} resubmitted a revised proposal for "
                 f"{inv['network_name']} · {inv['position_name']} at ${int(new['offer_amount_usd']):,}. "
                 "Review the updated offer."),
        entity_type="campaign", entity_id=new["id"],
        link="/admin/proposals-review",
        severity="action_required",
    )
    return _finalize(new, user)


@router.post("/{proposal_id}/archive")
async def archive_banner_proposal(proposal_id: str,
                                   body: ProposalArchiveBody,
                                   admin: dict = Depends(require_admin)):
    doc = await db.campaigns.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.get("is_archived"):
        return _finalize(doc, admin)

    entry = history_entry("archived", admin, internal_notes=(body.reason or "").strip())
    await db.campaigns.update_one({"id": proposal_id},
                                   {"$set": {"is_archived": True,
                                              "archived_at": now_iso(),
                                              "archived_by": admin["id"]},
                                    "$push": {"history": entry}})
    await audit(admin, "proposal.banner.archived", "campaign", proposal_id,
                {"reason": body.reason or ""})
    updated = await db.campaigns.find_one({"id": proposal_id})
    return _finalize(updated, admin)


@router.post("/{proposal_id}/unarchive")
async def unarchive_banner_proposal(proposal_id: str,
                                     admin: dict = Depends(require_admin)):
    doc = await db.campaigns.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc.get("is_archived"):
        return _finalize(doc, admin)
    entry = history_entry("unarchived", admin)
    await db.campaigns.update_one({"id": proposal_id},
                                   {"$set": {"is_archived": False,
                                              "archived_at": "",
                                              "archived_by": ""},
                                    "$push": {"history": entry}})
    await audit(admin, "proposal.banner.unarchived", "campaign", proposal_id, {})
    updated = await db.campaigns.find_one({"id": proposal_id})
    return _finalize(updated, admin)


@router.get("/{proposal_id}/proposal.pdf")
async def download_banner_proposal_pdf(proposal_id: str,
                                        user: dict = Depends(get_current_user)):
    """Premium sales-quality proposal PDF for approved banner campaigns.

    Available to the owning representative and administrators once the proposal
    has been approved.
    """
    doc = await db.campaigns.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if user["role"] not in ADMIN_ROLES and doc.get("rep_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    if doc.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Proposal PDF is only available after approval")

    doc.pop("_id", None)
    if user["role"] not in ADMIN_ROLES:
        doc = strip_internal_notes(doc)  # never leak internal notes into the PDF for reps

    pdf_bytes = generate_proposal_pdf(doc)
    ref = (doc.get("id") or "")[:8]
    filename = f"IMN-proposal-{ref}.pdf"
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
                              headers={"Content-Disposition": f'inline; filename="{filename}"'})
