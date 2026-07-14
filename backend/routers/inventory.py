"""Banner inventory (CPM per country) — read for all, edit for admins."""
from fastapi import APIRouter, Depends

from core import db, now_iso
from models import BannerInventoryItem
from security import get_current_user, require_admin
from audit_helper import audit

router = APIRouter(tags=["inventory"])


@router.get("/banner-inventory")
async def get_banner_inventory(user: dict = Depends(get_current_user)):
    items = await db.banner_inventory.find({}).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items


@router.put("/admin/banner-inventory/{country_code}")
async def update_inventory_item(country_code: str, body: BannerInventoryItem,
                                 admin: dict = Depends(require_admin)):
    doc = body.model_dump()
    doc["country_code"] = country_code.upper()
    doc["updated_at"] = now_iso()
    await db.banner_inventory.update_one({"country_code": country_code.upper()},
                                          {"$set": doc}, upsert=True)
    await audit(admin, "inventory.update", "banner_inventory", country_code.upper(),
                {"price_cpm_usd": doc["price_cpm_usd"]})
    return doc
