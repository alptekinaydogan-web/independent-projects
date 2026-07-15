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
