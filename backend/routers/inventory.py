"""Inventory catalog — network × position products across the Independent Media Network."""
from fastapi import APIRouter, Depends
from networks_data import NETWORKS, POSITIONS, all_inventory
from security import get_current_user

router = APIRouter(tags=["inventory"])


@router.get("/inventory")
async def get_inventory(user: dict = Depends(get_current_user)):
    return {
        "networks": sorted(NETWORKS, key=lambda n: n["order"]),
        "positions": sorted(POSITIONS, key=lambda p: p["order"]),
        "items": all_inventory(),
    }
