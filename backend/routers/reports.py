"""Operational reports — proposal counts + activity + CSV export.

Reporting is intentionally operational: counts, statuses, network activity.
No revenue, margin or profit — those belong to the representative's private
commercial relationship with their customer.
"""
import csv
import io
from collections import defaultdict
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from core import db, ADMIN_ROLES
from security import get_current_user, require_admin
from networks_data import all_inventory

router = APIRouter(tags=["reports"])


@router.get("/reports/overview")
async def reports_overview(user: dict = Depends(get_current_user)):
    is_admin = user["role"] in ADMIN_ROLES
    scope = {} if is_admin else {"rep_id": user["id"]}
    # Reports are lifecycle-facing — active proposals only (exclude archived)
    live_scope = {**scope, "is_archived": {"$ne": True}}

    banner_by_status = defaultdict(int)
    async for c in db.campaigns.find(live_scope):
        banner_by_status[c.get("status", "pending_review")] += 1

    tv_by_status = defaultdict(int)
    async for s in db.sponsorships.find(live_scope):
        tv_by_status[s.get("status", "pending_review")] += 1

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

    network_activity = defaultdict(int)
    async for c in db.campaigns.find({**scope, "status": "approved"}):
        network_activity[c.get("network_name") or "—"] += 1
    top_networks = sorted(network_activity.items(), key=lambda x: -x[1])[:8]

    payload = {
        "role": user["role"],
        "banner_proposals": {
            "pending_review": banner_by_status.get("pending_review", 0),
            "revised": banner_by_status.get("revised", 0),
            "approved": banner_by_status.get("approved", 0),
            "rejected": banner_by_status.get("rejected", 0),
            "revision_requested": banner_by_status.get("revision_requested", 0),
            "total": sum(banner_by_status.values()),
        },
        "tv_proposals": {
            "pending_review": tv_by_status.get("pending_review", 0),
            "revised": tv_by_status.get("revised", 0),
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
            + payload["banner_proposals"]["revised"]
            + payload["tv_proposals"]["revised"]
        )
        payload["archived_proposals_count"] = (
            await db.campaigns.count_documents({"is_archived": True})
            + await db.sponsorships.count_documents({"is_archived": True})
        )

    return payload


# ---------- CSV export (admin only) ----------
CSV_COLUMNS = [
    "kind", "proposal_id", "parent_proposal_id", "status", "is_archived",
    "created_at", "decided_at", "archived_at",
    "rep_name", "agency_name", "client_reference", "proposal_name",
    "inventory_network", "inventory_position", "tv_project_title",
    "episodes", "impressions", "start_date", "end_date",
    "offer_amount_usd",
    "representative_feedback", "internal_notes",
    "last_decision_actor", "history_length",
]


def _iso_month_bounds(month: Optional[str]):
    """Return (start_iso, end_iso_exclusive) for YYYY-MM, or (None, None)."""
    if not month:
        return None, None
    try:
        y, m = month.split("-")
        y = int(y); m = int(m)
    except Exception:
        return None, None
    start = datetime(y, m, 1)
    end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    return start.isoformat(), end.isoformat()


def _decision_actor(history):
    if not isinstance(history, list):
        return ""
    for h in reversed(history):
        if h.get("status") in ("approved", "rejected", "revision_requested"):
            return f"{h.get('actor_name', '')} ({h.get('actor_role', '')})"
    return ""


def _row_from_campaign(c: dict) -> dict:
    return {
        "kind": "banner",
        "proposal_id": c.get("id", ""),
        "parent_proposal_id": c.get("parent_proposal_id") or "",
        "status": c.get("status", ""),
        "is_archived": "yes" if c.get("is_archived") else "no",
        "created_at": c.get("created_at", ""),
        "decided_at": c.get("decided_at", ""),
        "archived_at": c.get("archived_at", ""),
        "rep_name": c.get("rep_name", ""),
        "agency_name": c.get("agency_name", ""),
        "client_reference": c.get("client_reference", ""),
        "proposal_name": c.get("campaign_name") or c.get("proposal_name", ""),
        "inventory_network": c.get("network_name", ""),
        "inventory_position": c.get("position_name", ""),
        "tv_project_title": "",
        "episodes": "",
        "impressions": c.get("impressions") or "",
        "start_date": c.get("start_date") or "",
        "end_date": c.get("end_date") or "",
        "offer_amount_usd": c.get("offer_amount_usd", ""),
        "representative_feedback": c.get("representative_feedback") or c.get("admin_notes") or "",
        "internal_notes": c.get("internal_notes", ""),
        "last_decision_actor": _decision_actor(c.get("history")),
        "history_length": len(c.get("history") or []),
    }


def _row_from_sponsorship(s: dict) -> dict:
    eps = s.get("episode_numbers") or []
    return {
        "kind": "sponsorship",
        "proposal_id": s.get("id", ""),
        "parent_proposal_id": s.get("parent_proposal_id") or "",
        "status": s.get("status", ""),
        "is_archived": "yes" if s.get("is_archived") else "no",
        "created_at": s.get("created_at", ""),
        "decided_at": s.get("decided_at", ""),
        "archived_at": s.get("archived_at", ""),
        "rep_name": s.get("rep_name", ""),
        "agency_name": s.get("agency_name", ""),
        "client_reference": s.get("client_reference", ""),
        "proposal_name": s.get("proposal_name", ""),
        "inventory_network": "",
        "inventory_position": "",
        "tv_project_title": s.get("tv_project_title", ""),
        "episodes": ",".join(str(e) for e in eps),
        "impressions": "",
        "start_date": "",
        "end_date": "",
        "offer_amount_usd": s.get("offer_amount_usd", ""),
        "representative_feedback": s.get("representative_feedback") or s.get("admin_notes") or "",
        "internal_notes": s.get("internal_notes", ""),
        "last_decision_actor": _decision_actor(s.get("history")),
        "history_length": len(s.get("history") or []),
    }


@router.get("/reports/proposals/export.csv")
async def export_proposals_csv(admin: dict = Depends(require_admin),
                                month: Optional[str] = Query(None, description="YYYY-MM filter"),
                                kind: str = Query("all", description="all|banner|tv"),
                                include_archived: bool = Query(True)):
    start_iso, end_iso = _iso_month_bounds(month)
    base: dict = {}
    if start_iso and end_iso:
        base["created_at"] = {"$gte": start_iso, "$lt": end_iso}
    if not include_archived:
        base["is_archived"] = {"$ne": True}

    rows = []
    if kind in ("all", "banner"):
        async for c in db.campaigns.find(base).sort("created_at", -1):
            rows.append(_row_from_campaign(c))
    if kind in ("all", "tv"):
        async for s in db.sponsorships.find(base).sort("created_at", -1):
            rows.append(_row_from_sponsorship(s))

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    buf.seek(0)

    tag = month or datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"imh-proposals-{kind}-{tag}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
