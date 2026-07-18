"""Pydantic models used across Independent Projects routers."""
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


# ---- Commercial proposal for banner inventory ----
class BannerProposalCreate(BaseModel):
    proposal_name: str
    client_reference: str          # rep's internal label (never disclosed to admin as identity)
    inventory_id: str              # "{network_key}__{position_key}"
    impressions: Optional[int] = None  # optional — subject to negotiation
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    offer_amount_usd: float        # what the rep offers to pay IMN for the placement
    notes: Optional[str] = ""


# ---- Commercial proposal for TV sponsorship ----
class TVProposalCreate(BaseModel):
    proposal_name: str
    client_reference: str
    tv_project_id: str
    episode_numbers: List[int]
    offer_amount_usd: float
    notes: Optional[str] = ""


class ProposalDecisionBody(BaseModel):
    decision: str  # approved | rejected | revision_requested
    # Split notes into two channels — reps only see `representative_feedback`
    representative_feedback: Optional[str] = ""
    internal_notes: Optional[str] = ""
    # Legacy field: if set, treated as `representative_feedback` for backward compat
    admin_notes: Optional[str] = ""


class ProposalArchiveBody(BaseModel):
    reason: Optional[str] = ""


class ProposalDuplicateOverrides(BaseModel):
    """Optional overrides carried by the rep from the duplicate action.
    All fields are optional — omitted fields inherit the parent proposal.
    """
    proposal_name: Optional[str] = None
    client_reference: Optional[str] = None
    impressions: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    offer_amount_usd: Optional[float] = None
    notes: Optional[str] = None
    episode_numbers: Optional[List[int]] = None


# ---- TV projects (editorial + inventory only, NO fixed price) ----
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
    # Independent Projects — enriched project package fields
    category: Optional[str] = "tv_formats"     # tv_formats | events | podcasts | documentaries | ...
    duration_minutes: Optional[int] = None
    difficulty: Optional[str] = ""             # entry | intermediate | advanced
    concept: Optional[str] = ""
    purpose: Optional[str] = ""
    audience_demographics: Optional[str] = ""
    audience_interests: Optional[str] = ""
    production_format: Optional[str] = ""
    technical_specs: Optional[dict] = None     # cameras / resolution / frame_rates / audio / graphics / delivery
    brand_guidelines: Optional[dict] = None    # logo / intro / outro / music / fonts / opening / closing
    sponsorship_opportunities: Optional[List[str]] = None  # informational only
    download_assets: Optional[List[dict]] = None           # [{label, url, filetype}]


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
    category: Optional[str] = None
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


class ApplyToProduceBody(BaseModel):
    tv_project_id: str
    message: Optional[str] = ""
    target_launch_date: Optional[str] = ""


class TVProjectStatusUpdate(BaseModel):
    status: str  # active | draft | closed


# ---- Editorial TV proposal (concept pitching) — unchanged from before ----
class ProposalCreate(BaseModel):
    title: str
    format: str
    country: str
    description: str
    estimated_episodes: int
    budget_hint_usd: Optional[float] = 0


class ProposalDecision(BaseModel):
    status: str
    admin_notes: Optional[str] = ""


class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class MarkReadBody(BaseModel):
    ids: Optional[List[str]] = None
