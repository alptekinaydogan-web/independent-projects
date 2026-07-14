"""Independent Media Hub - Backend Server
FastAPI + MongoDB, JWT auth, closed B2B platform.
"""
from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import logging
import bcrypt
import jwt as pyjwt
import secrets
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, Header, Query
from fastapi.responses import Response as FastResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field

# ---------- Configuration ----------
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
ACCESS_TTL = timedelta(hours=8)
REFRESH_TTL = timedelta(days=7)
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = os.environ.get("APP_NAME", "independent-media-hub")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("imh")

app = FastAPI(title="Independent Media Hub API")
api = APIRouter(prefix="/api")

# ---------- Countries ----------
COUNTRIES = [
    # Europe
    ("GB", "United Kingdom", "Europe"), ("DE", "Germany", "Europe"), ("FR", "France", "Europe"),
    ("IT", "Italy", "Europe"), ("ES", "Spain", "Europe"), ("NL", "Netherlands", "Europe"),
    ("SE", "Sweden", "Europe"), ("NO", "Norway", "Europe"), ("DK", "Denmark", "Europe"),
    ("FI", "Finland", "Europe"), ("PL", "Poland", "Europe"), ("PT", "Portugal", "Europe"),
    ("CH", "Switzerland", "Europe"), ("AT", "Austria", "Europe"), ("BE", "Belgium", "Europe"),
    ("IE", "Ireland", "Europe"), ("GR", "Greece", "Europe"), ("CZ", "Czech Republic", "Europe"),
    ("RO", "Romania", "Europe"), ("HU", "Hungary", "Europe"),
    # North America
    ("US", "United States", "North America"), ("CA", "Canada", "North America"), ("MX", "Mexico", "North America"),
    # South America
    ("BR", "Brazil", "South America"), ("AR", "Argentina", "South America"), ("CL", "Chile", "South America"),
    ("CO", "Colombia", "South America"), ("PE", "Peru", "South America"),
    # Asia
    ("JP", "Japan", "Asia"), ("CN", "China", "Asia"), ("IN", "India", "Asia"),
    ("KR", "South Korea", "Asia"), ("SG", "Singapore", "Asia"), ("TH", "Thailand", "Asia"),
    ("ID", "Indonesia", "Asia"), ("MY", "Malaysia", "Asia"), ("VN", "Vietnam", "Asia"),
    ("PH", "Philippines", "Asia"),
    # Middle East
    ("AE", "United Arab Emirates", "Middle East"), ("SA", "Saudi Arabia", "Middle East"),
    ("IL", "Israel", "Middle East"), ("TR", "Turkey", "Middle East"), ("QA", "Qatar", "Middle East"),
    # Africa
    ("ZA", "South Africa", "Africa"), ("NG", "Nigeria", "Africa"), ("EG", "Egypt", "Africa"),
    ("KE", "Kenya", "Africa"), ("MA", "Morocco", "Africa"),
    # Oceania
    ("AU", "Australia", "Oceania"), ("NZ", "New Zealand", "Oceania"),
]

DEFAULT_PRICES = {
    "North America": 42.0, "Europe": 35.0, "Oceania": 30.0,
    "Middle East": 28.0, "Asia": 22.0, "South America": 18.0, "Africa": 15.0,
}

# ---------- Auth Helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {"sub": user_id, "email": email, "role": role,
               "exp": datetime.now(timezone.utc) + ACCESS_TTL, "type": "access"}
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + REFRESH_TTL, "type": "refresh"}
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none",
                        max_age=int(ACCESS_TTL.total_seconds()), path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none",
                        max_age=int(REFRESH_TTL.total_seconds()), path="/")

def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_h = request.headers.get("Authorization", "")
        if auth_h.startswith("Bearer "):
            token = auth_h[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user

async def require_rep(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ("representative", "admin"):
        raise HTTPException(status_code=403, detail="Representative access required")
    return user

# ---------- Storage ----------
_storage_key: Optional[str] = None

def init_storage() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=180)
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key}, timeout=120)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# ---------- Models ----------
class LoginBody(BaseModel):
    email: EmailStr
    password: str

class ForgotPwBody(BaseModel):
    email: EmailStr

class ResetPwBody(BaseModel):
    token: str
    new_password: str

class RepresentativeCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    agency_name: str
    country: str
    is_active: bool = True

class RepresentativeUpdate(BaseModel):
    name: Optional[str] = None
    agency_name: Optional[str] = None
    country: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class BannerInventoryItem(BaseModel):
    country_code: str
    country_name: str
    region: str
    price_cpm_usd: float
    min_impressions: int = 10000

class CampaignCreate(BaseModel):
    campaign_name: str
    client_name: str
    country_codes: List[str]
    impressions: int
    client_total_price: float
    notes: Optional[str] = ""

class TVProjectCreate(BaseModel):
    title: str
    tagline: Optional[str] = ""
    synopsis: str
    hero_image_url: Optional[str] = ""
    demo_video_url: Optional[str] = ""
    target_audience: Optional[str] = ""
    distribution: Optional[str] = ""
    languages: List[str] = []
    total_episodes: int
    price_per_episode_usd: float
    sponsorship_rights: Optional[str] = ""
    status: str = "active"  # active | draft | closed

class TVProjectUpdate(BaseModel):
    title: Optional[str] = None
    tagline: Optional[str] = None
    synopsis: Optional[str] = None
    hero_image_url: Optional[str] = None
    demo_video_url: Optional[str] = None
    target_audience: Optional[str] = None
    distribution: Optional[str] = None
    languages: Optional[List[str]] = None
    total_episodes: Optional[int] = None
    price_per_episode_usd: Optional[float] = None
    sponsorship_rights: Optional[str] = None
    status: Optional[str] = None

class SponsorshipCreate(BaseModel):
    tv_project_id: str
    client_name: str
    episode_numbers: List[int]
    client_total_price: float
    notes: Optional[str] = ""

class ProposalCreate(BaseModel):
    title: str
    format: str  # documentary | interview_series | travel | investigation | other
    country: str
    description: str
    estimated_episodes: int
    budget_hint_usd: Optional[float] = 0

class ProposalDecision(BaseModel):
    status: str  # approved | rejected | in_review
    admin_notes: Optional[str] = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def strip_id(doc: dict) -> dict:
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


# ---------- Auth Routes ----------
@api.post("/auth/login")
async def login(body: LoginBody, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(user["id"], user["email"], user["role"])
    refresh = create_refresh_token(user["id"])
    set_auth_cookies(response, access, refresh)
    strip_id(user); user.pop("password_hash", None)
    return {"user": user, "access_token": access}

@api.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookies(response)
    return {"ok": True}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

@api.post("/auth/forgot-password")
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
        logger.info(f"[PASSWORD RESET] link for {email}: /reset-password?token={token}")
    return {"ok": True, "message": "If the email exists, a reset link has been sent."}

@api.post("/auth/reset-password")
async def reset_password(body: ResetPwBody):
    rec = await db.password_reset_tokens.find_one({"token": body.token, "used": False})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    if rec["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    await db.users.update_one({"id": rec["user_id"]},
                              {"$set": {"password_hash": hash_password(body.new_password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True}})
    return {"ok": True}


# ---------- Countries ----------
@api.get("/countries")
async def list_countries(user: dict = Depends(get_current_user)):
    return [{"code": c, "name": n, "region": r} for c, n, r in COUNTRIES]


# ---------- Admin: Representatives ----------
@api.get("/admin/representatives")
async def list_reps(_: dict = Depends(require_admin)):
    reps = await db.users.find({"role": "representative"}).to_list(500)
    for r in reps:
        r.pop("_id", None); r.pop("password_hash", None)
    return reps

@api.post("/admin/representatives")
async def create_rep(body: RepresentativeCreate, _: dict = Depends(require_admin)):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = {
        "id": str(uuid.uuid4()), "email": email, "password_hash": hash_password(body.password),
        "name": body.name, "role": "representative", "agency_name": body.agency_name,
        "country": body.country, "is_active": body.is_active, "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    user.pop("password_hash", None); user.pop("_id", None)
    return user

@api.patch("/admin/representatives/{rep_id}")
async def update_rep(rep_id: str, body: RepresentativeUpdate, _: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
    if updates:
        await db.users.update_one({"id": rep_id, "role": "representative"}, {"$set": updates})
    doc = await db.users.find_one({"id": rep_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Representative not found")
    doc.pop("_id", None); doc.pop("password_hash", None)
    return doc

@api.delete("/admin/representatives/{rep_id}")
async def delete_rep(rep_id: str, _: dict = Depends(require_admin)):
    res = await db.users.delete_one({"id": rep_id, "role": "representative"})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ---------- Banner Inventory ----------
@api.get("/banner-inventory")
async def get_banner_inventory(user: dict = Depends(get_current_user)):
    items = await db.banner_inventory.find({}).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items

@api.put("/admin/banner-inventory/{country_code}")
async def update_inventory_item(country_code: str, body: BannerInventoryItem,
                                _: dict = Depends(require_admin)):
    doc = body.model_dump()
    doc["country_code"] = country_code.upper()
    doc["updated_at"] = now_iso()
    await db.banner_inventory.update_one({"country_code": country_code.upper()},
                                          {"$set": doc}, upsert=True)
    return doc


# ---------- Banner Campaigns ----------
@api.get("/campaigns")
async def list_campaigns(user: dict = Depends(get_current_user)):
    q = {} if user["role"] == "admin" else {"rep_id": user["id"]}
    items = await db.campaigns.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items

@api.post("/campaigns")
async def create_campaign(body: CampaignCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives create campaigns")
    inv = {i["country_code"]: i async for i in db.banner_inventory.find({"country_code": {"$in": [c.upper() for c in body.country_codes]}})}
    if len(inv) != len(body.country_codes):
        raise HTTPException(status_code=400, detail="One or more selected countries have no inventory")
    # internal cost = sum of CPM * impressions/1000 per country
    per_country = []
    total_internal = 0.0
    for c in body.country_codes:
        row = inv[c.upper()]
        cost = round(row["price_cpm_usd"] * body.impressions / 1000.0, 2)
        per_country.append({"country_code": c.upper(), "country_name": row["country_name"],
                            "price_cpm_usd": row["price_cpm_usd"], "internal_cost": cost})
        total_internal += cost
    campaign = {
        "id": str(uuid.uuid4()), "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "campaign_name": body.campaign_name, "client_name": body.client_name,
        "country_codes": [c.upper() for c in body.country_codes],
        "per_country": per_country,
        "impressions": body.impressions,
        "internal_cost_usd": round(total_internal, 2),
        "client_total_price_usd": body.client_total_price,
        "margin_usd": round(body.client_total_price - total_internal, 2),
        "notes": body.notes, "status": "confirmed",
        "created_at": now_iso(),
    }
    await db.campaigns.insert_one(campaign)
    campaign.pop("_id", None)
    return campaign


# ---------- TV Projects ----------
@api.get("/tv-projects")
async def list_tv_projects(user: dict = Depends(get_current_user)):
    items = await db.tv_projects.find({}).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
        i["sponsored_episode_count"] = await db.sponsorships.count_documents(
            {"tv_project_id": i["id"]}) or 0
        # compute unique sponsored episodes
        cur = db.sponsorships.find({"tv_project_id": i["id"]})
        eps = set()
        async for s in cur:
            for e in s.get("episode_numbers", []):
                eps.add(e)
        i["sponsored_episodes"] = sorted(eps)
    return items

@api.get("/tv-projects/{project_id}")
async def get_tv_project(project_id: str, user: dict = Depends(get_current_user)):
    p = await db.tv_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(status_code=404, detail="TV project not found")
    p.pop("_id", None)
    cur = db.sponsorships.find({"tv_project_id": project_id})
    eps: dict = {}
    async for s in cur:
        for e in s.get("episode_numbers", []):
            eps[e] = {"episode": e, "sponsor_agency": s.get("agency_name", ""),
                      "client_name": s.get("client_name", "")}
    p["sponsored_episodes"] = list(eps.values())
    return p

@api.post("/admin/tv-projects")
async def create_tv_project(body: TVProjectCreate, _: dict = Depends(require_admin)):
    doc = body.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = now_iso()
    await db.tv_projects.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/admin/tv-projects/{project_id}")
async def update_tv_project(project_id: str, body: TVProjectUpdate, _: dict = Depends(require_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.tv_projects.update_one({"id": project_id}, {"$set": updates})
    doc = await db.tv_projects.find_one({"id": project_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc.pop("_id", None)
    return doc

@api.delete("/admin/tv-projects/{project_id}")
async def delete_tv_project(project_id: str, _: dict = Depends(require_admin)):
    res = await db.tv_projects.delete_one({"id": project_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ---------- Sponsorships ----------
@api.get("/sponsorships")
async def list_sponsorships(user: dict = Depends(get_current_user)):
    q = {} if user["role"] == "admin" else {"rep_id": user["id"]}
    items = await db.sponsorships.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items

@api.post("/sponsorships")
async def create_sponsorship(body: SponsorshipCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives can sponsor")
    project = await db.tv_projects.find_one({"id": body.tv_project_id})
    if not project:
        raise HTTPException(status_code=404, detail="TV project not found")
    # Ensure requested episodes are not already sponsored
    cur = db.sponsorships.find({"tv_project_id": body.tv_project_id})
    taken = set()
    async for s in cur:
        for e in s.get("episode_numbers", []):
            taken.add(e)
    for e in body.episode_numbers:
        if e in taken:
            raise HTTPException(status_code=409, detail=f"Episode {e} already sponsored")
        if e < 1 or e > project["total_episodes"]:
            raise HTTPException(status_code=400, detail=f"Invalid episode {e}")
    internal_cost = round(project["price_per_episode_usd"] * len(body.episode_numbers), 2)
    sponsorship = {
        "id": str(uuid.uuid4()), "tv_project_id": body.tv_project_id,
        "tv_project_title": project["title"],
        "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "client_name": body.client_name,
        "episode_numbers": sorted(body.episode_numbers),
        "episode_count": len(body.episode_numbers),
        "internal_cost_usd": internal_cost,
        "client_total_price_usd": body.client_total_price,
        "margin_usd": round(body.client_total_price - internal_cost, 2),
        "notes": body.notes, "status": "confirmed",
        "created_at": now_iso(),
    }
    await db.sponsorships.insert_one(sponsorship)
    sponsorship.pop("_id", None)
    return sponsorship


# ---------- Proposals ----------
@api.get("/proposals")
async def list_proposals(user: dict = Depends(get_current_user)):
    q = {} if user["role"] == "admin" else {"rep_id": user["id"]}
    items = await db.proposals.find(q).sort("created_at", -1).to_list(500)
    for i in items:
        i.pop("_id", None)
    return items

@api.post("/proposals")
async def create_proposal(body: ProposalCreate, user: dict = Depends(require_rep)):
    if user["role"] != "representative":
        raise HTTPException(status_code=403, detail="Only representatives can submit proposals")
    doc = body.model_dump()
    doc.update({
        "id": str(uuid.uuid4()), "rep_id": user["id"], "rep_name": user["name"],
        "agency_name": user.get("agency_name", ""),
        "status": "in_review", "admin_notes": "", "created_at": now_iso(),
    })
    await db.proposals.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api.patch("/admin/proposals/{proposal_id}")
async def decide_proposal(proposal_id: str, body: ProposalDecision, _: dict = Depends(require_admin)):
    if body.status not in ("approved", "rejected", "in_review"):
        raise HTTPException(status_code=400, detail="Invalid status")
    await db.proposals.update_one({"id": proposal_id},
                                   {"$set": {"status": body.status,
                                              "admin_notes": body.admin_notes or "",
                                              "decided_at": now_iso()}})
    doc = await db.proposals.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc.pop("_id", None)
    return doc


# ---------- Reports ----------
@api.get("/reports/overview")
async def reports_overview(user: dict = Depends(get_current_user)):
    is_admin = user["role"] == "admin"
    scope = {} if is_admin else {"rep_id": user["id"]}
    campaigns = await db.campaigns.find(scope).to_list(1000)
    sponsorships = await db.sponsorships.find(scope).to_list(1000)

    def sum_field(items, key):
        return round(sum(float(i.get(key, 0) or 0) for i in items), 2)

    country_totals: dict = {}
    for c in campaigns:
        for pc in c.get("per_country", []):
            country_totals.setdefault(pc["country_name"], 0)
            country_totals[pc["country_name"]] += pc.get("internal_cost", 0)
    top_countries = sorted(country_totals.items(), key=lambda x: -x[1])[:10]

    # monthly time series (last 6 months)
    from collections import defaultdict
    monthly = defaultdict(lambda: {"campaigns_usd": 0.0, "tv_usd": 0.0})
    for c in campaigns:
        m = c.get("created_at", "")[:7]
        monthly[m]["campaigns_usd"] += c.get("client_total_price_usd", 0)
    for s in sponsorships:
        m = s.get("created_at", "")[:7]
        monthly[m]["tv_usd"] += s.get("client_total_price_usd", 0)
    monthly_series = sorted(
        [{"month": k, "campaigns_usd": round(v["campaigns_usd"], 2),
          "tv_usd": round(v["tv_usd"], 2)} for k, v in monthly.items()],
        key=lambda x: x["month"])[-6:]

    total_reps = 0
    if is_admin:
        total_reps = await db.users.count_documents({"role": "representative", "is_active": True})

    proposals_pending = 0
    if is_admin:
        proposals_pending = await db.proposals.count_documents({"status": "in_review"})

    return {
        "role": user["role"],
        "campaign_count": len(campaigns),
        "sponsorship_count": len(sponsorships),
        "campaigns_client_revenue_usd": sum_field(campaigns, "client_total_price_usd"),
        "campaigns_internal_cost_usd": sum_field(campaigns, "internal_cost_usd"),
        "campaigns_margin_usd": sum_field(campaigns, "margin_usd"),
        "tv_client_revenue_usd": sum_field(sponsorships, "client_total_price_usd"),
        "tv_internal_cost_usd": sum_field(sponsorships, "internal_cost_usd"),
        "tv_margin_usd": sum_field(sponsorships, "margin_usd"),
        "top_countries": [{"country": k, "internal_usd": round(v, 2)} for k, v in top_countries],
        "monthly_series": monthly_series,
        "total_reps_active": total_reps,
        "proposals_pending": proposals_pending,
    }


# ---------- File Uploads (admin) ----------
@api.post("/admin/upload")
async def upload_file(file: UploadFile = File(...), kind: str = Form("image"),
                      user: dict = Depends(require_admin)):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin").lower()
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{kind}/{file_id}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    doc = {
        "id": file_id, "storage_path": result["path"],
        "original_filename": file.filename, "content_type": file.content_type,
        "size": result.get("size", len(data)), "kind": kind,
        "uploaded_by": user["id"], "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.files.insert_one(doc)
    doc.pop("_id", None)
    # Return public URL served by our backend
    backend_prefix = os.environ.get("BACKEND_PUBLIC_URL", "")
    doc["url"] = f"/api/files/{result['path']}"
    return doc

@api.get("/files/{path:path}")
async def serve_file(path: str, auth: Optional[str] = Query(None),
                      authorization: Optional[str] = Header(None)):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = get_object(path)
    except Exception as e:
        logger.error(f"file fetch error: {e}")
        raise HTTPException(status_code=502, detail="Storage error")
    return FastResponse(content=data, media_type=rec.get("content_type") or content_type)


# ---------- Startup: indexes + seed ----------
@app.on_event("startup")
async def startup():
    # indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.banner_inventory.create_index("country_code", unique=True)
    await db.campaigns.create_index("rep_id")
    await db.tv_projects.create_index("id", unique=True)
    await db.sponsorships.create_index("rep_id")
    await db.sponsorships.create_index("tv_project_id")
    await db.proposals.create_index("rep_id")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)

    # storage init (non-blocking; log on failure)
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.warning(f"Storage init failed (uploads will not work until fixed): {e}")

    # seed admin
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": admin_email,
            "password_hash": hash_password(admin_pw),
            "name": "Platform Administrator", "role": "admin",
            "is_active": True, "created_at": now_iso(),
        })
        logger.info(f"Seeded admin {admin_email}")
    elif not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email},
                                   {"$set": {"password_hash": hash_password(admin_pw)}})

    # seed sample representatives
    sample_reps = [
        {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!",
         "name": "Victor Laurent", "agency_name": "Paris Media Group", "country": "FR"},
        {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!",
         "name": "Amelia Hart", "agency_name": "London House Media", "country": "GB"},
    ]
    for r in sample_reps:
        if not await db.users.find_one({"email": r["email"]}):
            await db.users.insert_one({
                "id": str(uuid.uuid4()), "email": r["email"],
                "password_hash": hash_password(r["password"]),
                "name": r["name"], "role": "representative",
                "agency_name": r["agency_name"], "country": r["country"],
                "is_active": True, "created_at": now_iso(),
            })

    # seed banner inventory
    if await db.banner_inventory.count_documents({}) == 0:
        for code, name, region in COUNTRIES:
            await db.banner_inventory.insert_one({
                "country_code": code, "country_name": name, "region": region,
                "price_cpm_usd": DEFAULT_PRICES[region],
                "min_impressions": 10000,
                "updated_at": now_iso(),
            })

    # seed TV projects
    if await db.tv_projects.count_documents({}) == 0:
        samples = [
            {
                "title": "World of Girls",
                "tagline": "A global journey through the lives, dreams and challenges of young women.",
                "synopsis": "A 100-episode documentary series filmed across 40 countries, portraying the diverse realities of young women in 2026. Each episode is a self-contained story with cinematic production values.",
                "hero_image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600",
                "demo_video_url": "",
                "target_audience": "Adults 25-54, socially engaged, culturally curious",
                "distribution": "Independent TV + national broadcast partners in 40 countries",
                "languages": ["English", "French", "Spanish", "Arabic", "Mandarin"],
                "total_episodes": 100, "price_per_episode_usd": 300,
                "sponsorship_rights": "Opening credit, closing credit, one 15s sponsor spot mid-roll, digital pre-roll on VOD.",
                "status": "active",
            },
            {
                "title": "The Investigators",
                "tagline": "An interview series with the world's most fearless investigative journalists.",
                "synopsis": "24 in-depth interviews. One journalist per episode. Deep, unhurried, editorial conversations that let the story breathe.",
                "hero_image_url": "https://images.unsplash.com/photo-1640130541949-aa5d40f9635d?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600",
                "demo_video_url": "",
                "target_audience": "Executives, policy makers, cultural elite",
                "distribution": "Independent TV, YouTube, curated syndication",
                "languages": ["English"],
                "total_episodes": 24, "price_per_episode_usd": 900,
                "sponsorship_rights": "Presenting sponsor billing, one dedicated 30s spot, logo integration.",
                "status": "active",
            },
            {
                "title": "Silent Continents",
                "tagline": "A cinematic exploration of the natural landscapes that shape our planet.",
                "synopsis": "12 episodes. Aerial cinematography, immersive sound design, and slow storytelling across six continents.",
                "hero_image_url": "https://images.unsplash.com/photo-1760637627433-e7de199a8243?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600",
                "demo_video_url": "",
                "target_audience": "Nature enthusiasts, families, premium travel audiences",
                "distribution": "Independent TV Global + airline in-flight partners",
                "languages": ["English", "German", "Japanese"],
                "total_episodes": 12, "price_per_episode_usd": 1800,
                "sponsorship_rights": "Full episode presenting sponsor. Two dedicated spots. Digital rights included.",
                "status": "active",
            },
        ]
        for s in samples:
            s["id"] = str(uuid.uuid4()); s["created_at"] = now_iso()
            await db.tv_projects.insert_one(s)

    # write test credentials
    creds_dir = Path("/app/memory")
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / "test_credentials.md").write_text(
        f"""# Independent Media Hub – Test Credentials

## Administrator
- Email: `{os.environ['ADMIN_EMAIL']}`
- Password: `{os.environ['ADMIN_PASSWORD']}`
- Role: `admin`

## Representative accounts
- Email: `victor.laurent@parismedia.fr`  Password: `Rep2026!`  Agency: Paris Media Group (FR)
- Email: `amelia.hart@londonhouse.co.uk`  Password: `Rep2026!`  Agency: London House Media (GB)

## Auth endpoints
- POST /api/auth/login  {{ email, password }}
- POST /api/auth/logout
- GET  /api/auth/me
- POST /api/auth/forgot-password
- POST /api/auth/reset-password
""")

app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown():
    client.close()
