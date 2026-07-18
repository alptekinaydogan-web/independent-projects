"""Pydantic models used across Independent Projects routers.

Post-cleanup: banner/sponsorship marketplace models have been removed.
The platform now revolves exclusively around the Project Library
(TV Formats today, extensible to Events / Podcasts / etc. tomorrow),
the Apply-to-Produce workflow, and Partner project submissions.
"""
from typing import List, Optional
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
    phone: Optional[str] = ""
    website: Optional[str] = ""
    territory: Optional[str] = ""
    is_active: bool = True


class RepresentativeUpdate(BaseModel):
    name: Optional[str] = None
    agency_name: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    territory: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


# ---- Project Library — modular project package ----
# Category slug is stored as an entity reference (`category_slug`) rather than
# a free-text value, so future categories (Events, Podcasts, Documentaries,
# ...) can be introduced without a schema change.
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
    sponsorship_rights: Optional[str] = ""
    status: str = "active"  # active | draft | closed
    # Reference to a category entity (default seed = "tv_formats")
    category_slug: Optional[str] = "tv_formats"
    duration_minutes: Optional[int] = None
    difficulty: Optional[str] = ""             # entry | intermediate | advanced
    concept: Optional[str] = ""
    purpose: Optional[str] = ""
    audience_demographics: Optional[str] = ""
    audience_interests: Optional[str] = ""
    production_format: Optional[str] = ""
    technical_specs: Optional[dict] = None
    brand_guidelines: Optional[dict] = None
    sponsorship_opportunities: Optional[List[str]] = None
    download_assets: Optional[List[dict]] = None


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
    sponsorship_rights: Optional[str] = None
    status: Optional[str] = None
    category_slug: Optional[str] = None
    duration_minutes: Optional[int] = None
    difficulty: Optional[str] = None
    concept: Optional[str] = None
    purpose: Optional[str] = None
    audience_demographics: Optional[str] = None
    audience_interests: Optional[str] = None
    production_format: Optional[str] = None
    technical_specs: Optional[dict] = None
    brand_guidelines: Optional[dict] = None
    sponsorship_opportunities: Optional[List[str]] = None
    download_assets: Optional[List[dict]] = None


class TVProjectStatusUpdate(BaseModel):
    status: str  # active | draft | closed


class ApplyToProduceBody(BaseModel):
    # Route reads the project id from the URL path (`/tv-projects/{id}/apply`);
    # this field is preserved for backwards compatibility but is optional.
    tv_project_id: Optional[str] = None
    message: Optional[str] = ""
    target_launch_date: Optional[str] = ""


class ApplicationDecisionBody(BaseModel):
    decision: str  # approved | rejected | revision_requested
    representative_feedback: Optional[str] = ""
    internal_notes: Optional[str] = ""


# ---- Partner project submissions (new project ideas from Country Partners) ----
class ProposalCreate(BaseModel):
    title: str
    format: str
    country: str
    description: str
    estimated_episodes: int
    budget_hint_usd: Optional[float] = 0


class ProposalDecision(BaseModel):
    status: str  # approved | rejected | in_review (revision requested)
    admin_notes: Optional[str] = ""


class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class MarkReadBody(BaseModel):
    ids: Optional[List[str]] = None
