"""Owner-only: manage administrator accounts."""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import db, now_iso, ADMIN_ROLES
from models import AdminCreate
from security import hash_password, require_owner
from audit_helper import audit

router = APIRouter(prefix="/owner/admins", tags=["owner"])


@router.get("")
async def list_admins(_: dict = Depends(require_owner)):
    admins = await db.users.find({"role": {"$in": list(ADMIN_ROLES)}}).to_list(200)
    for a in admins:
        a.pop("_id", None); a.pop("password_hash", None)
    return admins


@router.post("")
async def create_admin(body: AdminCreate, owner: dict = Depends(require_owner)):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already exists")
    doc = {
        "id": str(uuid.uuid4()), "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name, "role": "admin",
        "is_active": True, "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    await audit(owner, "admin.create", "user", doc["id"], {"email": doc["email"]})
    doc.pop("password_hash", None); doc.pop("_id", None)
    return doc


@router.delete("/{admin_id}")
async def delete_admin(admin_id: str, owner: dict = Depends(require_owner)):
    target = await db.users.find_one({"id": admin_id})
    if not target:
        raise HTTPException(status_code=404, detail="Not found")
    if target.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the owner account")
    if target.get("role") != "admin":
        raise HTTPException(status_code=400, detail="Target is not an administrator")
    await db.users.delete_one({"id": admin_id})
    await audit(owner, "admin.delete", "user", admin_id, {"email": target["email"]})
    return {"ok": True}
