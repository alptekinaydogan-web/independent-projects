"""Operational reports — Project Library activity + Partner submissions.

Reporting is intentionally operational: application counts by status,
production coverage, partner submissions volume. No revenue, no margin,
no pricing — the commercial relationship with the customer stays with the
country partner.
"""
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends

from core import db, ADMIN_ROLES
from security import get_current_user

router = APIRouter(tags=["reports"])


@router.get("/reports/overview")
async def reports_overview(user: dict = Depends(get_current_user)):
    is_admin = user["role"] in ADMIN_ROLES
    scope = {} if is_admin else {"rep_id": user["id"]}

    # ---- Applications by status ----
    apps_by_status: defaultdict[str, int] = defaultdict(int)
    async for a in db.productions.find(scope):
        apps_by_status[a.get("status", "submitted")] += 1

    # ---- Partner project submissions by status ----
    partner_by_status: defaultdict[str, int] = defaultdict(int)
    async for p in db.proposals.find(scope):
        partner_by_status[p.get("status", "in_review")] += 1

    # ---- Monthly activity (applications + partner submissions) ----
    monthly = defaultdict(lambda: {"applications": 0, "approved_applications": 0,
                                    "partner_submissions": 0, "partner_approved": 0})
    async for a in db.productions.find(scope):
        m = (a.get("created_at") or "")[:7]
        monthly[m]["applications"] += 1
        if a.get("status") == "approved":
            monthly[m]["approved_applications"] += 1
    async for p in db.proposals.find(scope):
        m = (p.get("created_at") or "")[:7]
        monthly[m]["partner_submissions"] += 1
        if p.get("status") == "approved":
            monthly[m]["partner_approved"] += 1
    monthly_series = sorted(
        [{"month": k, **v} for k, v in monthly.items()],
        key=lambda x: x["month"])[-6:]

    # ---- Project library composition ----
    projects_by_status: defaultdict[str, int] = defaultdict(int)
    async for tp in db.tv_projects.find({}):
        projects_by_status[tp.get("status", "draft")] += 1

    # ---- Most-produced projects (approved applications) ----
    project_production_counts: defaultdict[str, int] = defaultdict(int)
    async for a in db.productions.find({"status": "approved"}):
        project_production_counts[a.get("tv_project_title") or "—"] += 1
    top_projects = sorted(project_production_counts.items(), key=lambda x: -x[1])[:8]

    payload = {
        "role": user["role"],
        "applications": {
            "submitted": apps_by_status.get("submitted", 0),
            "revision_requested": apps_by_status.get("revision_requested", 0),
            "approved": apps_by_status.get("approved", 0),
            "rejected": apps_by_status.get("rejected", 0),
            "total": sum(apps_by_status.values()),
        },
        "partner_submissions": {
            "in_review": partner_by_status.get("in_review", 0),
            "approved": partner_by_status.get("approved", 0),
            "rejected": partner_by_status.get("rejected", 0),
            "total": sum(partner_by_status.values()),
        },
        "monthly_series": monthly_series,
        "top_projects": [{"project": k, "productions": v} for k, v in top_projects],
        "project_library": {
            "active": projects_by_status.get("active", 0),
            "draft": projects_by_status.get("draft", 0),
            "closed": projects_by_status.get("closed", 0),
            "total": sum(projects_by_status.values()),
        },
    }

    if is_admin:
        payload["total_reps_active"] = await db.users.count_documents(
            {"role": "representative", "is_active": True})
        payload["all_pending_review"] = (
            payload["applications"]["submitted"]
            + payload["applications"]["revision_requested"]
            + payload["partner_submissions"]["in_review"]
        )

    return payload
