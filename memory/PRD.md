# Independent Projects — Product Requirements Document

## 1. Vision
Independent Projects is the premium international **Project Library** of the Independent Media Network. Country Partners discover, download, localize and produce high-quality media projects under one unified global standard.

**Not** an advertising marketplace. **Not** a self-service portal. **Closed B2B** platform for authorized representatives only.

## 2. User Roles
- **Owner / Administrator** — publishes projects, reviews production applications and partner project submissions, manages representatives.
- **Representative (Country Partner)** — licensed commercial partner. Browses the Project Library, applies to produce projects in their territory, submits new project ideas.

There is no public access, no sign-up, no marketing homepage.

## 3. Commercial Model — Only two primitives
1. **Project Library** — modular project packages (TV Formats today; extensible to Events / Podcasts / Documentaries / Research / Co-Productions).
2. **Apply-to-Produce workflow + Partner project submissions** — country partners register intent to produce an existing project OR pitch a new one.

No banner marketplace. No pricing. No bidding. Commercial relationship with the customer stays with the country partner.

## 4. Architecture

### Backend (FastAPI + MongoDB)
- **routers/tv.py** — Project Library (list/get, admin CRUD, status, applications lifecycle).
- **routers/proposals.py** — Partner project submissions (new project ideas).
- **routers/representatives.py** — Rep CRUD + CRM profile aggregations.
- **routers/categories.py** — Read-only category catalog (extensible).
- **routers/reports.py** — Applications + Partner submissions operational reports.
- **routers/scheduler_admin.py** — System health + owner-only demo reseed.
- **routers/auth.py**, **routers/audit_log.py**, **routers/uploads.py**, **routers/owner.py**, **routers/reference.py**.
- **notifications.py** — in-platform notifications (bell + notifications center).

### Frontend (React + Shadcn UI)
- **components/project/ProjectBlocks.jsx** — reusable modular content blocks (Hero, Overview, Audience, Format, Sponsorship, TechnicalSpecs, BrandGuidelines, DownloadCenter, ApplyToProduce).
- **pages/rep/TVProjectDetail.jsx** composes these blocks. Future categories reuse the blocks.
- **Admin** routes: Dashboard, Project Library, Applications Review (new), Partner Submissions, Representatives, Reports, Audit Log, Administrators.
- **Rep** routes: Dashboard, Browse Projects, Submit a Project, Notifications, Activity.

### Categories — future-proof
`categories` collection with a single seed document `{ slug: "tv_formats" }`. Future categories are added by inserting new documents — no schema/code change required. The category selector is intentionally NOT surfaced in the UI today.

## 5. Data Model (key collections)
- `users`: {id, email, password_hash, role, name, agency_name, country, phone, website, territory, is_active, created_at}
- `categories`: {id, slug, name, description, order, is_active, created_at}
- `tv_projects`: modular project package — {id, title, tagline, synopsis, hero_image_url, demo_video_url, target_audience, distribution, languages[], total_episodes, sponsorship_rights, status, category_slug, concept, purpose, audience_demographics, audience_interests, production_format, technical_specs{}, brand_guidelines{}, sponsorship_opportunities[], download_assets[]}
- `productions` (production applications): {id, tv_project_id, tv_project_title, rep_id, rep_name, agency_name, country, message, target_launch_date, status ∈ submitted|approved|rejected|revision_requested, representative_feedback, internal_notes, decided_at, created_at}
- `proposals` (partner project submissions): {id, title, format, country, description, estimated_episodes, budget_hint_usd, rep_id, rep_name, agency_name, status ∈ in_review|approved|rejected, admin_notes, decided_at, created_at}
- `audit_log`, `notifications`.

Legacy `campaigns`, `sponsorships`, `banner_inventory` collections are dropped on startup.

## 6. Implemented (Iteration 21 — 2026-02-25)
- Full backend cleanup: removed banner marketplace routers (campaigns, inventory), PDF generation, network data, proposal history, scheduler.
- Removed banner-era frontend pages (InventoryCatalog, InventoryDetail, Campaigns, CampaignBuilder, Sponsorships, ProposalHistoryDrawer, DuplicateProposalDialog, old ProposalsReview).
- Added `routers/categories.py` + seeded `tv_formats` document.
- Rewrote `tv.py`, `reports.py`, `representatives.py`, `models.py`, `server.py`, `seed.py`, `demo_seed.py`, `scheduler_admin.py`, `email_service.py`.
- Rewrote frontend dashboards, reports, catalog, TVProjectDetail (modular), RepresentativeProfile.
- Added `pages/admin/ApplicationsReview.jsx` for the Apply-to-Produce review workflow.
- 16/16 backend tests pass. 100% frontend Playwright flows pass.

## 7. Backlog
- **P2** Multi-category rollout — implement Events / Podcasts / Documentaries / Research / Co-Productions when business is ready. Frontend catalog + admin category chip picker.
- **P2** Move `list_tv_projects` counts to a single `$facet` aggregation when catalog exceeds ~200 projects.
- **P3** System Observability upgrade — decision latency, last Resend delivery, background task history.
- **P3** Extract sponsorship_opportunities / download_assets into their own admin edit UI (currently inline JSON on the project document).

## 8. Test Credentials
See `/app/memory/test_credentials.md`.
