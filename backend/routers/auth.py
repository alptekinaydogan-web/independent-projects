"""Auth endpoints: login, logout, /me, forgot/reset password."""
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Response, Depends

from core import db, now_iso, logger
from models import LoginBody, ForgotPwBody, ResetPwBody
from security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    set_auth_cookies, clear_auth_cookies, get_current_user,
)
from email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginBody, response: Response):
    email = body.email.lower().strip()
    logger.info(f"[auth/login] attempt email={email}")
    try:
        user = await db.users.find_one({"email": email})
    except Exception:
        # Explicit log + explicit 503 with a JSON detail so the frontend
        # shows a real reason instead of a generic "Something went wrong"
        # (which is what nginx-level 502/504 HTML pages collapse to).
        logger.exception(f"[auth/login] MongoDB lookup failed for {email}")
        raise HTTPException(status_code=503,
                             detail="Authentication service is temporarily unavailable (database unreachable).")

    if not user:
        logger.info(f"[auth/login] no user for {email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_active", True):
        logger.info(f"[auth/login] user inactive: {email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        pw_ok = verify_password(body.password, user["password_hash"])
    except Exception:
        # bcrypt / passlib blow-up on a corrupted hash. Return 401 (not
        # 500) so we don't leak the internal issue, but log the trace.
        logger.exception(f"[auth/login] password verify raised for {email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not pw_ok:
        logger.info(f"[auth/login] bad password for {email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = create_access_token(user["id"], user["email"], user["role"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    # Track last-login timestamp for the CRM (best-effort — never blocks login)
    try:
        await db.users.update_one({"id": user["id"]}, {"$set": {"last_login_at": now_iso()}})
    except Exception:
        logger.exception(f"[auth/login] last_login_at update failed for {email}")
    user.pop("_id", None); user.pop("password_hash", None)
    logger.info(f"[auth/login] success email={email} role={user.get('role')}")
    return {"user": user, "access_token": access}


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/forgot-password")
async def forgot_password(body: ForgotPwBody):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token, "user_id": user["id"],
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False, "created_at": now_iso(),
        })
        await send_password_reset_email(user["email"], user.get("name", ""), token)
    return {"ok": True, "message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPwBody):
    rec = await db.password_reset_tokens.find_one({"token": body.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    exp = rec["expires_at"]
    if getattr(exp, "tzinfo", None) is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    await db.users.update_one({"id": rec["user_id"]},
                              {"$set": {"password_hash": hash_password(body.new_password)}})
    # invalidate all outstanding tokens for that user
    await db.password_reset_tokens.update_many(
        {"user_id": rec["user_id"], "used": False},
        {"$set": {"used": True}})
    return {"ok": True}
