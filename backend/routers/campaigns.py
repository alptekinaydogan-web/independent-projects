"""Banner campaigns — create by rep, list by rep/admin. Includes flight dates."""
import uuid
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso, ADMIN_ROLES
from models import CampaignCreate
from security import get_current_user, require_rep
from audit_helper import audit
from notifications import notify_all_admins

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _parse_date(s: str) -> date:
    """Parse YYYY-MM-DD or ISO datetime string to a date."""
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date() if "T" in s else datetime.strptime(s, "%Y-%m-%d").date()


def _campaign_status(start: str, end: str) -> str:
    if not end:
        return "confirmed"
    try:
        today = datetime.now(timezone.utc).date()
        e = _parse_date(end)
        s = _parse_date(start) if start else today
        if today < s:
            return "pending"
        if today > e:
            return "expired"
        return "active"
    except Exception:
        return "confirmed"


def _decorate(c: dict) -> dict:
    """Attach computed status + days_left. Never mutates DB."""
    c.pop("_id", None)
    c["computed_status"] = _campaign_status(c.get("start_date", ""), c.get("end_date", ""))
    if c.get("end_date"):
        try:
            c["days_left"] = (_parse_date(c["end_date"]) - datetime.now(timezone.utc).date()).days
        except Exception:
            c["days_left"] = None
    else:
        c["days_left"] = None
    return c


@router.get("")
async def list_campaigns(user: dict = Depends(get_current_user)):
    q = {} if user["role"] in ADMIN_ROLES else {"rep_id": user["id"]}
    items = await db.campaigns.find(q).sort("created_at", -1).to_list(500)
    return [_decorate(i) for i in items]


@router.post("")
async def create_campaign(body: CampaignCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives create campaigns")

    # Validate flight dates
    start_date = body.start_date or datetime.now(timezone.utc).date().isoformat()
    end_date = body.end_date
    if end_date:
        try:
            sd = _parse_date(start_date)
            ed = _parse_date(end_date)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
        if ed < sd:
            raise HTTPException(status_code=400, detail="End date must be on or after start date")

    inv = {i["country_code"]: i async for i in db.banner_inventory.find(
        {"country_code": {"$in": [c.upper() for c in body.country_codes]}})}
    if len(inv) != len(body.country_codes):
        raise HTTPException(status_code=400, detail="One or more selected countries have no inventory")

    per_country = []
    total_internal = 0.0
    total_impressions = 0
    overrides = body.per_country_impressions or {}
    for c in body.country_codes:
        row = inv[c.upper()]
        imp = int(overrides.get(c.upper(), body.impressions))
        cost = round(row["price_cpm_usd"] * imp / 1000.0, 2)
        per_country.append({
            "country_code": c.upper(), "country_name": row["country_name"],
            "price_cpm_usd": row["price_cpm_usd"], "impressions": imp,
            "internal_cost": cost,
        })
        total_internal += cost
        total_impressions += imp

    campaign = {
        "id": str(uuid.uuid4()), "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "campaign_name": body.campaign_name, "client_name": body.client_name,
        "country_codes": [c.upper() for c in body.country_codes],
        "per_country": per_country,
        "impressions": body.impressions,
        "total_impressions": total_impressions,
        "internal_cost_usd": round(total_internal, 2),
        "client_total_price_usd": body.client_total_price,
        "margin_usd": round(body.client_total_price - total_internal, 2),
        "start_date": start_date,
        "end_date": end_date or "",
        "notes": body.notes, "status": "confirmed",
        "created_at": now_iso(),
    }
    await db.campaigns.insert_one(campaign)

    await audit(user, "campaign.create", "campaign", campaign["id"], {
        "campaign_name": campaign["campaign_name"], "client_name": campaign["client_name"],
        "countries": len(campaign["country_codes"]),
        "internal_cost_usd": campaign["internal_cost_usd"],
        "client_total_price_usd": campaign["client_total_price_usd"],
        "start_date": start_date, "end_date": end_date or "",
    })

    date_note = f" · Flights {start_date} → {end_date}" if end_date else ""
    await notify_all_admins(
        event_type="campaign.created",
        title=f"New banner campaign booked · {campaign['campaign_name']}",
        message=(f"{user.get('agency_name', user['name'])} booked a {len(campaign['country_codes'])}-country campaign "
                 f"for {campaign['client_name']} at ${int(campaign['client_total_price_usd']):,} client price.{date_note}"),
        entity_type="campaign", entity_id=campaign["id"],
        link="/admin/reports",
        severity="info",
    )

    return _decorate(campaign)
