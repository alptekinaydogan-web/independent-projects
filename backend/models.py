"""Pydantic models used across Independent Media Hub routers."""
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr


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
    per_country_impressions: Optional[Dict[str, int]] = None
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


class TVProjectStatusUpdate(BaseModel):
    status: str  # active | draft | closed


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


class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class MarkReadBody(BaseModel):
    ids: Optional[List[str]] = None
