"""Pydantic models used across Independent Projects routers.

Post-unification: every project (whether created directly by an Admin or
submitted by a Country Partner) lives in the same `tv_projects`
collection and shares one Project model. Distinction is carried by
`source` ("admin" | "partner") and `moderation_status`
("draft" | "submitted" | "revision_requested" | "approved" | "rejected").
Approved partner submissions become Official Projects in-place — no
recreation.
"""
from typing import List, Optional, Any
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


# ---- Unified Project model ----
class TVProjectCreate(BaseModel):
    # Basic
    title: str
    subtitle: Optional[str] = ""
    tagline: Optional[str] = ""
    category_slug: Optional[str] = "tv_formats"
    status: Optional[str] = "draft"        # visibility: active | draft | closed
    hero_image_url: Optional[str] = ""
    demo_video_url: Optional[str] = ""
    gallery: Optional[List[str]] = None

    # Executive Summary
    overview: Optional[str] = ""
    purpose: Optional[str] = ""
    why_exists: Optional[str] = ""
    key_selling_points: Optional[List[str]] = None

    # Story & Concept
    concept: Optional[str] = ""
    narrative: Optional[str] = ""
    episode_structure: Optional[str] = ""
    tone: Optional[str] = ""

    # Legacy synopsis kept in sync with overview for backward compat
    synopsis: Optional[str] = ""

    # Objectives
    objective_entertainment: Optional[str] = ""
    objective_education: Optional[str] = ""
    objective_awareness: Optional[str] = ""
    objective_commercial: Optional[str] = ""

    # Target Audience
    target_audience: Optional[str] = ""
    audience_demographics: Optional[str] = ""
    audience_interests: Optional[str] = ""
    audience_geography: Optional[str] = ""
    audience_viewing_habits: Optional[str] = ""

    # Production Format
    total_episodes: Optional[int] = 0
    episode_duration: Optional[int] = None
    production_workflow: Optional[str] = ""
    required_crew: Optional[str] = ""
    locations: Optional[str] = ""
    equipment: Optional[str] = ""
    distribution: Optional[str] = ""
    languages: Optional[List[str]] = None
    production_format: Optional[str] = ""
    difficulty: Optional[str] = ""

    # Sponsorship (informational)
    sponsorship_opportunities: Optional[List[str]] = None
    sponsorship_rights: Optional[str] = ""

    # Technical Specifications
    technical_specs: Optional[dict] = None

    # Brand Guidelines
    brand_guidelines: Optional[dict] = None

    # Download Center (uploads managed via /api/projects/{id}/assets)
    download_assets: Optional[List[dict]] = None


class TVProjectUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    tagline: Optional[str] = None
    category_slug: Optional[str] = None
    status: Optional[str] = None
    hero_image_url: Optional[str] = None
    demo_video_url: Optional[str] = None
    gallery: Optional[List[str]] = None

    overview: Optional[str] = None
    purpose: Optional[str] = None
    why_exists: Optional[str] = None
    key_selling_points: Optional[List[str]] = None

    concept: Optional[str] = None
    narrative: Optional[str] = None
    episode_structure: Optional[str] = None
    tone: Optional[str] = None
    synopsis: Optional[str] = None

    objective_entertainment: Optional[str] = None
    objective_education: Optional[str] = None
    objective_awareness: Optional[str] = None
    objective_commercial: Optional[str] = None

    target_audience: Optional[str] = None
    audience_demographics: Optional[str] = None
    audience_interests: Optional[str] = None
    audience_geography: Optional[str] = None
    audience_viewing_habits: Optional[str] = None

    total_episodes: Optional[int] = None
    episode_duration: Optional[int] = None
    production_workflow: Optional[str] = None
    required_crew: Optional[str] = None
    locations: Optional[str] = None
    equipment: Optional[str] = None
    distribution: Optional[str] = None
    languages: Optional[List[str]] = None
    production_format: Optional[str] = None
    difficulty: Optional[str] = None

    sponsorship_opportunities: Optional[List[str]] = None
    sponsorship_rights: Optional[str] = None

    technical_specs: Optional[dict] = None
    brand_guidelines: Optional[dict] = None
    download_assets: Optional[List[dict]] = None


class TVProjectStatusUpdate(BaseModel):
    status: str  # active | draft | closed


class ProjectModerationBody(BaseModel):
    decision: str  # approved | rejected | revision_requested
    admin_feedback: Optional[str] = ""
    internal_notes: Optional[str] = ""


class ProjectPublishBody(BaseModel):
    published: bool


class ProjectFeatureBody(BaseModel):
    featured: bool


class ProjectArchiveBody(BaseModel):
    archived: bool


class ProjectAssetAdd(BaseModel):
    label: str
    url: str
    filetype: Optional[str] = ""
    storage_path: Optional[str] = ""
    original_filename: Optional[str] = ""


class ApplyToProduceBody(BaseModel):
    tv_project_id: Optional[str] = None  # optional; route reads id from path
    message: Optional[str] = ""
    target_launch_date: Optional[str] = ""


class ApplicationDecisionBody(BaseModel):
    decision: str  # approved | rejected | revision_requested
    representative_feedback: Optional[str] = ""
    internal_notes: Optional[str] = ""


# ---- Legacy proposal wire model ----
# Kept for backward compat with the old /api/proposals endpoint. New writes
# create a unified Project (source=partner) with a mapped subset of fields.
class ProposalCreate(BaseModel):
    title: str
    format: Optional[str] = "documentary"
    country: Optional[str] = ""
    description: Optional[str] = ""
    estimated_episodes: Optional[int] = 0
    budget_hint_usd: Optional[float] = 0


class ProposalDecision(BaseModel):
    status: str  # approved | rejected | in_review (== revision requested)
    admin_notes: Optional[str] = ""


class AdminCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class MarkReadBody(BaseModel):
    ids: Optional[List[str]] = None
