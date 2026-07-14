"""Operational reports — proposal counts + activity. NO revenue, margin or profit."""
from collections import defaultdict
from fastapi import APIRouter, Depends

from core import db, ADMIN_ROLES
from security import get_current_user
from networks_data import all_inventory

router = APIRouter(tags=["reports"])


@router.get("/reports/overview")
async def reports_overview(user: dict = Depends(get_current_user)):
    is_admin = user["role"] in ADMIN_ROLES
    scope = {} if is_admin else {"rep_id": user["id"]}

    banner_by_status = defaultdict(int)
    async for c in db.campaigns.find(scope):
        banner_by_status[c.get("status", "pending_review")] += 1

    tv_by_status = defaultdict(int)
    async for s in db.sponsorships.find(scope):
        tv_by_status[s.get("status", "pending_review")] += 1

    # Editorial proposals (concept pitches) — unchanged, count only
    editorial_by_status = defaultdict(int)
    async for p in db.proposals.find(scope):
        editorial_by_status[p.get("status", "in_review")] += 1

    monthly = defaultdict(lambda: {"banner_submitted": 0, "tv_submitted": 0,
                                    "banner_approved": 0, "tv_approved": 0})
    async for c in db.campaigns.find(scope):
        m = (c.get("created_at") or "")[:7]
        monthly[m]["banner_submitted"] += 1
        if c.get("status") == "approved":
            monthly[m]["banner_approved"] += 1
    async for s in db.sponsorships.find(scope):
        m = (s.get("created_at") or "")[:7]
        monthly[m]["tv_submitted"] += 1
        if s.get("status") == "approved":
            monthly[m]["tv_approved"] += 1
    monthly_series = sorted(
        [{"month": k, **v} for k, v in monthly.items()],
        key=lambda x: x["month"])[-6:]

    # Approved-per-network activity (banner)
    network_activity = defaultdict(int)
    async for c in db.campaigns.find({**scope, "status": "approved"}):
        network_activity[c.get("network_name") or "—"] += 1
    top_networks = sorted(network_activity.items(), key=lambda x: -x[1])[:8]

    payload = {
        "role": user["role"],
        "banner_proposals": {
            "pending_review": banner_by_status.get("pending_review", 0),
            "approved": banner_by_status.get("approved", 0),
            "rejected": banner_by_status.get("rejected", 0),
            "revision_requested": banner_by_status.get("revision_requested", 0),
            "total": sum(banner_by_status.values()),
        },
        "tv_proposals": {
            "pending_review": tv_by_status.get("pending_review", 0),
            "approved": tv_by_status.get("approved", 0),
            "rejected": tv_by_status.get("rejected", 0),
            "revision_requested": tv_by_status.get("revision_requested", 0),
            "total": sum(tv_by_status.values()),
        },
        "editorial_proposals": {
            "in_review": editorial_by_status.get("in_review", 0),
            "approved": editorial_by_status.get("approved", 0),
            "rejected": editorial_by_status.get("rejected", 0),
            "total": sum(editorial_by_status.values()),
        },
        "monthly_series": monthly_series,
        "top_networks": [{"network": k, "approved": v} for k, v in top_networks],
        "inventory_products_count": len(all_inventory()),
    }

    if is_admin:
        payload["total_reps_active"] = await db.users.count_documents(
            {"role": "representative", "is_active": True})
        payload["all_pending_review"] = (
            payload["banner_proposals"]["pending_review"]
            + payload["tv_proposals"]["pending_review"]
        )

    return payload
