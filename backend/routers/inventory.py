"""Inventory catalog — network × position products across the network.

Also exposes per-product detail with calendar-style availability so both
administrators (auditing offers) and representatives (planning campaigns) can
see reserved / active / expired periods before submitting a proposal.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from networks_data import NETWORKS, POSITIONS, all_inventory
from security import get_current_user
from core import db, ADMIN_ROLES

router = APIRouter(tags=["inventory"])

_INV_INDEX = {i["id"]: i for i in all_inventory()}


@router.get("/inventory")
async def get_inventory(_: dict = Depends(get_current_user)):
    return {
        "networks": sorted(NETWORKS, key=lambda n: n["order"]),
        "positions": sorted(POSITIONS, key=lambda p: p["order"]),
        "items": all_inventory(),
    }


def _lifecycle(start: str, end: str) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    if end and today > end[:10]:
        return "expired"
    if start and today < start[:10]:
        return "reserved"     # approved but not yet live
    return "active"


@router.get("/inventory/{inventory_id}")
async def inventory_detail(inventory_id: str, user: dict = Depends(get_current_user)):
    """Return the product spec + a calendar-friendly availability model.

    - Admins see EVERY offer (any status) for the inventory item.
    - Representatives see only their own offers + a redacted list of external
      reservations (agency + date range so they can plan around them).
    """
    inv = _INV_INDEX.get(inventory_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory product not found")

    q = {"inventory_id": inventory_id}
    offers_admin, offers_rep_view, reservations = [], [], []
    is_admin = user["role"] in ADMIN_ROLES

    async for c in db.campaigns.find(q).sort("start_date", 1):
        c.pop("_id", None)
        row = {
            "id": c["id"], "status": c.get("status"), "is_archived": c.get("is_archived", False),
            "start_date": (c.get("start_date") or "")[:10],
            "end_date":   (c.get("end_date")   or "")[:10],
            "rep_id": c.get("rep_id"), "agency_name": c.get("agency_name", ""),
            "campaign_name": c.get("campaign_name", ""),
            "offer_amount_usd": c.get("offer_amount_usd"),
            "lifecycle": _lifecycle(c.get("start_date") or "", c.get("end_date") or "") if c.get("status") == "approved" else None,
        }
        # Approved + non-archived proposals reserve the inventory window
        if c.get("status") == "approved" and not c.get("is_archived"):
            reservations.append({
                "id": c["id"],
                "start_date": row["start_date"], "end_date": row["end_date"],
                "agency_name": row["agency_name"], "lifecycle": row["lifecycle"],
                "is_yours": c.get("rep_id") == user["id"],
            })
        if is_admin:
            offers_admin.append(row)
        elif c.get("rep_id") == user["id"]:
            offers_rep_view.append(row)

    # Overall inventory-item lifecycle status is derived from reservations
    today = datetime.now(timezone.utc).date().isoformat()
    active_now = [r for r in reservations
                  if r["start_date"] and r["end_date"]
                  and r["start_date"] <= today <= r["end_date"]]
    upcoming = [r for r in reservations
                if r["start_date"] and r["start_date"] > today]

    if active_now:
        inventory_status = "active"       # a live approved campaign right now
    elif upcoming:
        inventory_status = "reserved"     # future approved reservation exists
    else:
        # Any expired reservations count as expired history only
        expired = [r for r in reservations if r["end_date"] and r["end_date"] < today]
        inventory_status = "expired" if expired and not upcoming and not active_now else "available"

    return {
        "inventory": inv,
        "status": inventory_status,
        "reservations": reservations,
        "offers": offers_admin if is_admin else offers_rep_view,
        "offers_count": len(offers_admin) if is_admin else None,
        "is_admin_view": is_admin,
    }


@router.get("/inventory/{inventory_id}/availability")
async def inventory_availability(inventory_id: str, user: dict = Depends(get_current_user)):
    """Compact calendar model — one bucket per month for the next 12 months,
    marked available / reserved / active based on approved reservations.
    """
    inv = _INV_INDEX.get(inventory_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory product not found")

    reservations = []
    async for c in db.campaigns.find({"inventory_id": inventory_id,
                                       "status": "approved",
                                       "is_archived": {"$ne": True}}):
        reservations.append({
            "start": (c.get("start_date") or "")[:10],
            "end":   (c.get("end_date") or "")[:10],
            "rep_id": c.get("rep_id"),
            "agency_name": c.get("agency_name", ""),
        })

    today = datetime.now(timezone.utc).date()
    months = []
    for i in range(-1, 12):
        y = today.year + (today.month - 1 + i) // 12
        m = ((today.month - 1 + i) % 12) + 1
        month_start = f"{y:04d}-{m:02d}-01"
        month_end = f"{y:04d}-{m:02d}-28"  # crude but effective; month collisions align
        state = "available"
        who = None
        for r in reservations:
            if not r["start"] or not r["end"]:
                continue
            if r["start"] <= month_end and r["end"] >= month_start:
                # any overlap counts. Prefer "active" over "reserved" over "expired"
                today_iso = today.isoformat()
                if r["start"] <= today_iso <= r["end"]:
                    state = "active"
                elif r["start"] > today_iso:
                    state = "reserved"
                else:
                    state = "expired"
                who = r["agency_name"]
                break
        months.append({"year": y, "month": m,
                        "label": datetime(y, m, 1).strftime("%b %Y"),
                        "state": state, "reserved_by": who})

    return {"inventory_id": inventory_id, "months": months}
