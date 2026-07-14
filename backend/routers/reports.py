"""Reports overview: scoped for admin/owner vs representative."""
from collections import defaultdict
from fastapi import APIRouter, Depends

from core import db, ADMIN_ROLES
from security import get_current_user

router = APIRouter(tags=["reports"])


def _sum_field(items, key):
    return round(sum(float(i.get(key, 0) or 0) for i in items), 2)


@router.get("/reports/overview")
async def reports_overview(user: dict = Depends(get_current_user)):
    is_admin = user["role"] in ADMIN_ROLES
    scope = {} if is_admin else {"rep_id": user["id"]}
    campaigns = await db.campaigns.find(scope).to_list(1000)
    sponsorships = await db.sponsorships.find(scope).to_list(1000)

    country_totals: dict = {}
    for c in campaigns:
        for pc in c.get("per_country", []):
            country_totals.setdefault(pc["country_name"], 0)
            country_totals[pc["country_name"]] += pc.get("internal_cost", 0)
    top_countries = sorted(country_totals.items(), key=lambda x: -x[1])[:10]

    monthly = defaultdict(lambda: {"campaigns_usd": 0.0, "tv_usd": 0.0})
    for c in campaigns:
        m = (c.get("created_at") or "")[:7]
        monthly[m]["campaigns_usd"] += c.get("client_total_price_usd", 0)
    for s in sponsorships:
        m = (s.get("created_at") or "")[:7]
        monthly[m]["tv_usd"] += s.get("client_total_price_usd", 0)
    monthly_series = sorted(
        [{"month": k, "campaigns_usd": round(v["campaigns_usd"], 2),
          "tv_usd": round(v["tv_usd"], 2)} for k, v in monthly.items()],
        key=lambda x: x["month"])[-6:]

    total_reps = 0
    proposals_pending = 0
    if is_admin:
        total_reps = await db.users.count_documents({"role": "representative", "is_active": True})
        proposals_pending = await db.proposals.count_documents({"status": "in_review"})

    return {
        "role": user["role"],
        "campaign_count": len(campaigns),
        "sponsorship_count": len(sponsorships),
        "campaigns_client_revenue_usd": _sum_field(campaigns, "client_total_price_usd"),
        "campaigns_internal_cost_usd": _sum_field(campaigns, "internal_cost_usd"),
        "campaigns_margin_usd": _sum_field(campaigns, "margin_usd"),
        "tv_client_revenue_usd": _sum_field(sponsorships, "client_total_price_usd"),
        "tv_internal_cost_usd": _sum_field(sponsorships, "internal_cost_usd"),
        "tv_margin_usd": _sum_field(sponsorships, "margin_usd"),
        "top_countries": [{"country": k, "internal_usd": round(v, 2)} for k, v in top_countries],
        "monthly_series": monthly_series,
        "total_reps_active": total_reps,
        "proposals_pending": proposals_pending,
    }
