"""Static country reference — used by campaign builder + rep forms."""
from fastapi import APIRouter, Depends
from countries_data import COUNTRIES
from security import get_current_user

router = APIRouter(tags=["countries"])


@router.get("/countries")
async def list_countries(user: dict = Depends(get_current_user)):
    return [{"code": c, "name": n, "region": r} for c, n, r in COUNTRIES]
