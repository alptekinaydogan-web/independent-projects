# Independent Media Hub — Product Requirements Document

## Original Problem Statement
Independent Media Hub is the commercial platform of Independent Media Network — a closed, invitation-only B2B platform for authorized representatives of the network. It is NOT a public marketplace, NOT Google Ads, NOT a self-service portal. Only two commercial modules:
1. **Banner Campaigns** — representatives sell banner inventory across countries/regions of the network.
2. **Independent TV Sponsorships** — representatives sponsor episodes of original Independent TV productions.

Representatives also submit **TV Project Proposals** for admin review.

## Architecture
- **Backend**: FastAPI + MongoDB (motor). JWT-based auth (bcrypt + httpOnly cookies + Bearer fallback). Emergent Object Storage for admin image/video uploads. All routes under `/api`.
- **Frontend**: React 19 (CRA) + TailwindCSS + Shadcn UI. Playfair Display + IBM Plex Sans/Mono. Editorial executive palette (F9F9F6 / 0A1128 / 0033A0).
- **Roles**: `admin`, `representative`. No public registration — admin seeds accounts.

## User Personas
- **Administrator** — owns the platform, manages representatives, banner inventory, TV projects, reviews proposals, monitors global reports.
- **Representative (Agency)** — licensed commercial partner with an existing client portfolio. Uses IMH to book banner campaigns and TV sponsorships for their customers with their own margins.

## Core Requirements (Static)
- No public site. Users arrive at premium split-screen login.
- Admin-only account creation. Two roles.
- Banner campaigns targetable across 1 / many / all countries.
- TV project presentation pages feel like investment proposals.
- Only internal (representative) prices in the platform. Representative sets their own client price.
- Proposals reviewed by admin only.

## What's Implemented (Feb 2026 · Iteration 19-20 · INDEPENDENT PROJECTS PIVOT)
- **Rename Independent Commerce → Independent Projects** globally. Sidebar wordmark, page metadata, all UI copy, documentation.
- **Banner Marketplace removed from UI** — banner inventory, offers, proposals-review Banner tab, banner nav items removed from BOTH admin and rep sidebars. Backend routes remain for backwards-compat data migration but are no longer surfaced.
- **TV Projects → Professional Project Packages** — new detail page (`/rep/tv/{id}`) with a dark hero (cover, trailer, category chip, status, duration, difficulty) + 7 informational sections: Concept & purpose, Target audience, Production format, Sponsorship opportunities (informational tiers, NO pricing), Technical specifications (cameras/resolution/frame rate/audio/graphics/delivery/subtitles/thumbnails), Brand guidelines (logo/intro/outro/music/fonts/motion), Download center (7 default assets: editable Sponsor Presentation, Production Bible, Brand Guidelines, Graphics Package, Intro & Outro, Thumbnail Templates, Submission Checklist).
- **Apply to Produce workflow** — new `POST /api/tv-projects/{id}/apply`, `GET /api/tv-projects/{id}/applications`, `GET /api/my-productions`. One active application per rep per project (409 duplicate). Rep-side detail page shows Apply-to-produce button → dialog with message + target launch date; on success turns into a green "Application submitted" badge.
- **Category architecture** — `category` field added to TV projects (default `tv_formats`). Structure ready for future categories (events, podcasts, documentaries, media_campaigns, research_projects, co_productions, special_projects) without further schema change.
- **Enriched TV project model** — new optional fields: `category`, `duration_minutes`, `difficulty`, `concept`, `purpose`, `audience_demographics`, `audience_interests`, `production_format`, `technical_specs` (dict), `brand_guidelines` (dict), `sponsorship_opportunities` (list), `download_assets` (list).
- **Admin sidebar reshaped** — 'Commercial' section replaced with 'Project Library' containing Project Library / Submissions Review / Partner Submissions. Rep sidebar reshaped: Overview + Project Library (Browse Projects, Submit a Project) + Insights (Activity).

## What's Implemented (Feb 2026 · Iteration 18 · PRODUCTION READY)
- **Representative creation crash FIXED** — the "Failed to execute removeChild on Node" error is eliminated. Root cause was Radix Select portal being unmounted mid-transition when the parent synchronously re-rendered the reps table on success. Fix: (1) switched country picker to a native `<select>` (no portal), (2) `setOpen(false)` → `setTimeout(0)` → `load()` so Radix Dialog unmount completes before `setReps()` replaces the tree. Verified across create + edit dialogs.
- **Representatives list — new management columns** — Agency, Representative (email underneath), Country, **Active**, **Pending**, **Approved**, **Last activity**, Status. Backend `GET /api/admin/representatives` returns each row enriched with `active_engagements`, `pending_offers`, `approved_offers`, `last_activity_at`.
- **Representative CRM profile — full rebuild** — 8-field identity grid (Email, Phone, Website, Country/Territory, Status, Registered, Approved on, Last login), 4 KPI cards (Banner offers, TV proposals, Active banner campaigns, Active TV sponsorships), Tabbed views: **Proposal history** with 8 filter chips (all / banner / sponsorship / approved / pending / revision / rejected / archived), **Active campaigns**, **Notifications** (fanned out by rep), **Timeline** (rep-as-actor + rep-as-entity audit stream with actor role). Inline administrative actions in the header — **Edit** (opens prefilled dialog for phone/website/territory/country), **Reset password** (browser prompt → PATCH), **Suspend/Reactivate** toggle.
- **User model extensions** — `phone`, `website`, `territory`, `approved_at`, `last_login_at` optional fields on user documents. `/api/auth/login` records `last_login_at` on every successful login (best-effort, never blocks login).
- **General stability confirmed** — 0 ErrorBoundary triggers across every admin + rep route in regression sweep. Sidebar shows "Commerce" brand and "Project Proposals" label. Every page renders without runtime exceptions.

## What's Implemented (Feb 2026 · Iteration 16-17 · FINAL QA POLISH)
- **Project rename** `Independent Media Hub` → `Independent Commerce` — sidebar wordmark, login page, page metadata (index.html title), page copy, seed messages, emails, PDF documents (via source strings). Cache-only leftovers.
- **Landing page copy** — new eyebrow `PRIVATE PARTNER PLATFORM`, headline `Built exclusively for Independent Media Network Partners.`, subheadline `A private commercial environment reserved exclusively for licensed Independent Media Network Partners.`
- **Navigation rename** — admin sidebar `Editorial Proposals` → `Project Proposals`; rep sidebar identical rename. New rep sidebar item `Banner Inventory` for direct catalog access.
- **Representative CRM profile page** (`/admin/representatives/{id}`) — identity fields (email, country, status, registration+approval), banner+TV stats cards with per-status breakdown, active-campaigns list, recent proposal history (30 items), timeline of the rep's own audit actions (50 items). Clickable from Representatives table row.
- **Banner Inventory as central object** — `GET /api/inventory/{id}` returns inventory + status (available/reserved/active/expired) + reservations + offers. `GET /api/inventory/{id}/availability` returns 13 color-coded monthly buckets. Detail page renders calendar grid + status badge + admin-vs-rep offer scoping.
- **Automatic duplicate-proposal prevention** — POST /api/campaigns now returns 409 when window overlaps an existing approved+non-archived proposal on the same inventory.
- **Representative creation crash** — `/api/countries` opened to any authenticated user (was admin-only, breaking the rep submit-proposal form).
- **Every page fails gracefully** — new `ErrorBoundary.jsx` component wraps `<Outlet />` in `AppShell`, keyed by pathname so navigation resets the boundary. If any page throws, sidebar stays operational and the boundary shows a "Section unavailable" panel with Try again button.

## What's Implemented (Feb 2026 · Iteration 13 · QA READY)
- **Demo environment seeder** — new `POST /api/admin/demo/seed` (owner-only) wipes `campaigns/sponsorships/notifications/audit_log/proposals` and rebuilds a realistic dataset covering EVERY lifecycle status. Produces: 17 banner proposals (3 submitted / 2 revised / 2 revision-requested / 6 approved / 2 rejected / 2 archived), 11 TV sponsorships (2 / 1 / 1 / 5 / 1 / 1), 11 role-fanned-out notifications (unread action-required + reminders + info), 54+ audit entries. Data is time-distributed over the past 6 months so the reports dashboard shows a real curve.
- **One-licensed-representative model** — Victor Laurent (Paris Media Group) is the active QA representative. Amelia Hart is marked `is_active=False` so the platform behaves as a single-rep environment while preserving referential integrity.
- **Dashboard reseed control** — owner-only `Reseed demo data` button in the admin dashboard header, with confirmation dialog + success toast. Non-owners never see the button.
- **Idempotent + audited** — every reseed writes an audit entry `demo.seed` with the summary payload. Running twice returns to a clean baseline.

## What's Implemented (Feb 2026 · Iteration 12)
- **Admin Dashboard vitals card** — new "System vitals" section on `/admin` consuming `GET /api/admin/system/health`. Five color-coded columns: Database (green/red with ping ms), Queue depth (background tasks outstanding), Email delivery (Live green / Dev fallback amber with sender), Scheduler (archive retention days + reminder thresholds), Uptime (since restart). Includes an overall status badge ("All systems normal" / "Degraded") in the top-right. Polls every 30 seconds while the tab is open so admins get a live pulse of platform health at a glance.

## What's Implemented (Feb 2026 · Iteration 11)
- **Admin Audit Log UI upgrade** — `/admin/audit-log` now exposes the new backend `action` filter with a curated preset dropdown (banner proposals, TV sponsorships, email deliveries, TV project management, representative management, admin management, inventory) AND a free-text prefix search. Free-text always wildcard-suffixed. Inline chip surfaces the effective filter; `Clear filters` resets everything. Action column shows the human label above the raw action key.
- **Operational health endpoint** — new `GET /api/admin/system/health` (owner/admin only) returns live vitals: DB reachability + latency, six-key collection counts, outstanding background-task count, email provider mode (live vs dev-fallback with sender), and scheduler configuration (reminder days + archive retention). Uses `db.command("ping")` for a real round-trip. Non-admin gets 403.

## What's Implemented (Feb 2026 · Iteration 10)
- **Audit-log action filter** — `GET /api/admin/audit-log` now accepts an `action` query parameter. Supports both exact match (e.g. `action=proposal.banner.approved`) and wildcard prefix match with a trailing asterisk (e.g. `action=proposal.banner.*`). Regex metacharacters are escaped so the prefix is interpreted literally. Composes cleanly with the existing `entity_type` and `actor_role` filters.
- **Tracked background-task registry** — new `background_tasks.py` module exposes `spawn(coro, name=...)` which schedules a coroutine on the event loop AND holds a strong reference until it completes (preventing garbage-collector cancellation) via a module-level `set()`. Every previously-fire-and-forget `asyncio.create_task(...)` call in the codebase (banner + sponsorship approval-email helpers) now uses `spawn()`.
- **Graceful shutdown** — `server.py::shutdown()` now `await`s `drain_background_tasks(timeout=10.0)` before closing the Mongo client, so any in-flight approved-proposal email delivery completes rather than being cancelled mid-flight.

## What's Implemented (Feb 2026 · Iteration 9)
- **Automatic proposal PDF email on approval** — when an admin approves any commercial proposal (banner or TV sponsorship), a fire-and-forget background task builds the branded PDF, base64-encodes it, and delivers it as an attachment to the owning representative via Resend. Uses the rep-facing view (internal notes already stripped) so the document is safe to forward to the customer. Never blocks the approval response.
- **Audit trail for delivery** — every attempted send writes an entry to `audit_log`: action `proposal.{banner|sponsorship}.pdf_emailed` on success, `..pdf_email_failed` on any upstream failure (dev-mode empty API key, Resend error, missing user record). Details record `to`, `ok`, `pdf_bytes`.
- **Beautiful email envelope** — matching the Independent Media Hub design system: editorial headline, "Proposal approved" eyebrow (green), IMN cover-block with the approved amount + reference, deep link back to the platform, and a confidential-footer.
- **Zero code change to deploy** — the flow is fully driven by env vars `RESEND_API_KEY` and `RESEND_FROM_EMAIL`. When empty (dev), a fallback log line captures the intended delivery so QA can verify without hitting Resend.

## What's Implemented (Feb 2026 · Iteration 8)
- **Premium commercial proposal PDF** — `GET /api/campaigns/{id}/proposal.pdf` and `GET /api/sponsorships/{id}/proposal.pdf` generate a branded, sales-quality multi-page A4 document using ReportLab. Available only to the owning rep + administrators once the proposal is approved. Layout: editorial cover, section on Independent Media Network, selected inventory (banner) or full TV project presentation with sponsorship rights + episode selection grid, dark commercial-terms block with the approved amount, and an official "Approved" green stamp block with approver / date / reference.
- **`strip_internal_notes()` gate** — the PDF endpoint strips internal notes before rendering for reps, guaranteeing confidential admin notes never leak into a document reps share with customers.
- **Sponsorship duplicate now supports episode override in the UI** — the DuplicateProposalDialog fetches the TV project on open and renders an episode picker grid. Selected = navy, Taken = disabled gray (episodes locked by OTHER approved proposals), Available = white with border. The rep's original episodes always stay selectable so they can retain them.
- **PDF download buttons everywhere** — rep sees a green "PROPOSAL PDF" button on every approved row in `/rep/banners` and `/rep/sponsorships`. Admin sees the same button on approved rows in `/admin/proposals-review`.
- **ReportLab pinned** to `reportlab==5.0.0` in `/app/backend/requirements.txt`.

## What's Implemented (Feb 2026 · Iteration 7)
- **Full proposal lifecycle history**: every commercial proposal (banner + TV sponsorship) carries an append-only `history` array. Statuses: `submitted → revision_requested → revised → approved | rejected → archived`. Each entry stores actor, timestamp, `representative_feedback` and `internal_notes`.
- **Split note channels**: admins now write two separate notes on every decision — `representative_feedback` (shared with rep) and `internal_notes` (admin-only, never exposed to reps). Backend strips `internal_notes` from every rep-facing response.
- **Duplicate & Revise workflow**: representatives can duplicate any `revision_requested` proposal directly from the list. A prefilled dialog lets them adjust only what changed; new proposal is created with `status="revised"` and `parent_proposal_id` back-linking to the original. Available for banner + sponsorship.
- **Proposal history drawer**: shared React component surfaces the complete lifecycle timeline. Rep view hides internal notes; admin view shows both channels.
- **Archive & retention**: admins can manually archive/unarchive any proposal. Background scheduler auto-archives finished proposals after `PROPOSAL_ARCHIVE_DAYS` (default 90) days beyond `end_date` (banner) or `decided_at` (sponsorship). Archived items remain searchable via `?include_archived=true`.
- **Admin CSV export** (`GET /api/reports/proposals/export.csv`): extended fields — proposal_id, parent_proposal_id, kind, status, is_archived, created_at, decided_at, archived_at, rep_name, agency_name, client_reference, proposal_name, inventory (network/position or TV title + episodes), impressions, flight dates, offer_amount_usd, representative_feedback, internal_notes, last_decision_actor, history_length. Filterable by month + kind + include_archived.
- **Resend production-ready**: `RESEND_API_KEY` and `RESEND_FROM_EMAIL` fully env-driven — no code changes needed for deployment. When key is empty, dev fallback logs reset links.

## What's Implemented (Feb 2026 · Iteration 6)
- **Commercial model = negotiated commercial proposals**. There are no fixed prices, no internal costs, no representative revenue, no margin, no client price anywhere in the platform. Representatives negotiate with their customers OFF-platform, then submit a confidential commercial proposal to Independent Media Network. Administrators approve / reject / request revision. Proposals are private per representative — reps never see each other's offers.
- **Inventory = network × position catalog**. 9 networks (Global + Tourism, Health, Real Estate, Education, Economy, Sports, Technology, Entertainment) × 10 standardized positions (Hero, Header, Sidebar Top/Bottom, Article Top/Middle/Bottom, Footer, Mobile, Sticky) = 90 products. Each product spans the entire network automatically; adding country sites does not require any UI change.
- **Two commercial modules, both proposal-based**: Banner Proposals and TV Sponsorship Proposals. Each has `pending_review → approved / rejected / revision_requested` lifecycle with admin decision endpoint + confidential notes.
- **Notification Center** — role-aware, categorized (`action_required`, `reminder`, `info`), soft-delete archive, dashboard "Needs your attention" strip, per-severity bell badge color, `campaign.expiring.30d/14d/7d/1d` reminders via background scheduler.
- **Operational reports & dashboards** — proposal counts by status, monthly submitted/approved trend, top networks purchased, inventory product count, active reps. Zero revenue metrics displayed.
- **Auth**: JWT + bcrypt + Resend-driven password reset (env-driven RESEND_API_KEY + RESEND_FROM_EMAIL).
- **Modular backend**: `server.py` orchestrator + `core / security / models / audit_helper / email_service / storage / notifications / networks_data / scheduler / seed / proposal_history / routers/*`.
- **Multi-role admins**: `owner` + `admin` + `representative`. Owner can create/remove admins.
- **Audit log**: every state-changing action logged.
- **Migration**: legacy campaigns/sponsorships from earlier iterations were auto-promoted to `approved` status and their revenue fields dropped.

## Prioritized Backlog
### P1 (post-first-finish)
- 2D world map for country selection in campaign builder (react-simple-maps).
- Per-country impressions override in campaign builder (currently uniform per country).
- Export campaigns/sponsorships as CSV/PDF proposals for representatives to hand to clients.
- Email delivery for password reset (currently link is logged to backend console only).
- Admin ability to freeze/close TV projects, and bulk-import inventory changes.
### P2
- Notifications center for proposal decisions.
- Audit log of admin actions.
- Multi-admin roles (reviewer vs owner).

## Next Tasks
1. (Optional P2) Auto-generated PDF proposal letters signed by Independent Media Network on approval, serving as a closable sales document for the rep's customer.
2. Consider revenue enhancement: exportable "Investment Memorandum" PDF for TV project pages so representatives can share the presentation with clients as a branded proposal.
