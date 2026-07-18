"""Categories — future-proof taxonomy for the Project Library.

At launch the library only surfaces a single category (TV Formats).
Storing categories as first-class entities means future categories
(Events, Podcasts, Documentaries, Media Campaigns, Research Projects,
Co-Productions, Special Projects) can be introduced without any
schema or code change — a new document in the `categories` collection
is enough.

The category selector is intentionally NOT surfaced in the UI today.
This router exposes a minimal read-only endpoint so the frontend can
render category chips consistently once more categories become active.
"""
from fastapi import APIRouter, Depends

from core import db
from security import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(_: dict = Depends(get_current_user),
                           include_inactive: bool = False):
    q = {} if include_inactive else {"is_active": True}
    items = await db.categories.find(q).sort("order", 1).to_list(100)
    for i in items:
        i.pop("_id", None)
    return items


@router.get("/{slug}")
async def get_category(slug: str, _: dict = Depends(get_current_user)):
    doc = await db.categories.find_one({"slug": slug})
    if not doc:
        return {"slug": slug, "name": slug.replace("_", " ").title(),
                "is_active": False, "description": ""}
    doc.pop("_id", None)
    return doc
