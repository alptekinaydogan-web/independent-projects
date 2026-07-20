# Independent Commerce — Product Requirements Document

> **Development freeze — 2026-02-25.** Product name is **Independent Commerce**. No further features until after successful production deployment.

## 1. Vision
Independent Commerce is the premium international **Project Library** of the Independent Media Network. Country Partners discover, download, localize and produce high-quality media projects under one unified global standard.

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

## 6. Implemented

### Iteration 23 — 2026-02-25 · Admin Read-First Review + Moderation Sidebar
- **New Admin project surface.** `/admin/tv-projects/{id}` now renders the FULL public Project Page (Hero + every modular block, same as `/rep/tv/{id}`) with a sticky right-hand **moderation panel**. Approve · Request revision · Reject · Publish · Feature · Archive · Internal notes · Edit project · Preview as partner all live in that sidebar.
- **Editor moved to a secondary route.** `/admin/tv-projects/{id}/edit` hosts the modular editor form. Editor's own Publish/Feature/Archive strip is suppressed here (`hideModerationStrip`) because those controls now belong to the AdminProjectView sidebar. Editor also has a `← Back to project page` link and returns the admin to the read view after Save.
- **Partner submissions inbox** now lands on the read view (not the form). Clicking a partner card → `/admin/tv-projects/{id}` → admin reviews the complete project → decides via the sidebar.
- **Applications & Revision history** rendered below the project page (admin-only blocks): applications by country partners, and a chronological log of every moderation decision.
- Verified: 14/14 backend regression + 100% frontend Playwright. Report: `/app/test_reports/iteration_23.json`.

### Iteration 22 — 2026-02-25 · Unified Project Editor
- **One editor everywhere.** `components/project/ProjectEditor.jsx` — used by both Admins and Country Partners.
- **Unified data model.** Admin projects and partner submissions share `tv_projects`, distinguished by `source` and `moderation_status`.
- **Approving a partner submission promotes it in place** — no recreation. Legacy `proposals` collection migrated on startup.
- New rep endpoints (POST /projects, PATCH /projects/{id}, POST /projects/{id}/submit, /assets, GET /my-projects) and admin moderation endpoints (/moderate, /publish, /feature, /archive).
- Rich content fields added: subtitle, gallery, key_selling_points, narrative, episode_structure, tone, objectives, audience geography/viewing habits, episode duration, crew, locations, equipment, brand palette/music/motion.

- **One editor everywhere.** New `components/project/ProjectEditor.jsx` — the single React component used by both Admins (`/admin/tv-projects/new` and `/admin/tv-projects/{id}`) and Country Partners (`/rep/projects/new` and `/rep/projects/{id}`). Sections: Basic Info · Executive Summary · Story & Concept · Objectives · Target Audience · Production Format · Sponsorship (informational) · Technical Specifications · Brand Guidelines · Download Center · Revision History.
- **Unified data model.** Admin projects and partner submissions now share `tv_projects`. Distinction lives in `source` (admin | partner) and `moderation_status` (draft | submitted | revision_requested | approved | rejected). Approved partner submissions become Official Projects in place — no recreation. Legacy `proposals` collection migrated on startup.
- **In-place partner review.** `/admin/proposals` renders a card inbox that links straight to the FULL editor with an inline moderation strip (Approve / Request revision / Reject).
- **Moderation controls.** New endpoints: `PATCH /admin/projects/{id}/moderate`, `.../publish`, `.../feature`, `.../archive`. Rep-owned draft lifecycle: `POST /projects`, `PATCH /projects/{id}`, `POST /projects/{id}/submit`, `DELETE /projects/{id}`, `POST/DELETE /projects/{id}/assets`.
- **Rich content fields** added to the Project model: subtitle, gallery, key_selling_points, narrative, episode_structure, tone, objective_entertainment/education/awareness/commercial, audience_geography/viewing_habits, episode_duration, production_workflow, required_crew, locations, equipment, brand palette + music + motion graphics. Read view (`/rep/tv/{id}`) renders these via new `ProjectConcept` + `ProjectObjectives` modular blocks.
- **Legacy adapters.** `/api/proposals` and `/api/admin/proposals/{id}` still function as thin adapters over the unified model (partner-source projects). Reports and CRM aggregate partner submissions from `tv_projects`.
- 16/16 new backend tests pass (`test_project_editor_unified.py`). 30/30 combined with iter21 regression file. 100% frontend Playwright flows.

### Iteration 21 — 2026-02-25 · Backend Cleanup + Categories
- Removed banner marketplace subsystem (campaigns/inventory/sponsorship/proposal PDF/scheduler + 5 orphaned frontend pages + 2 dialog components).
- Added future-proof `categories` collection seeded with `tv_formats`.
- Modular content blocks (`components/project/ProjectBlocks.jsx`).
- New `ApplicationsReview.jsx` page.

## 7. Backlog
- **P2** Roll out additional categories (Events / Podcasts / Documentaries / Research / Co-Productions) — architecture ready.
- **P2** Replace N+1 `count_documents` in `list_tv_projects` with a single `$facet` aggregation.
- **P3** System Observability upgrade (decision latency, last Resend delivery).

## 8. Test Credentials
See `/app/memory/test_credentials.md`.

