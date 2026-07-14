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

## What's Implemented (Feb 2026)
- **Modular backend architecture**: server.py is now a ~60-line orchestrator. Domain logic lives in `/app/backend/core.py` + `security.py` + `models.py` + `audit_helper.py` + `email_service.py` + `storage.py` + `notifications.py` + `countries_data.py` + `seed.py` + 11 focused routers under `/app/backend/routers/`.
- **Notification Center** — role-aware, non-noisy. Wired into: proposal submitted / approved / rejected / in-review, campaign booked, sponsorship confirmed, TV project launched / reopened / closed, and administrator actions affecting a rep (suspend, reactivate, admin-triggered password reset). Endpoints: `GET /api/notifications`, `GET /api/notifications/unread-count`, `PATCH /api/notifications/{id}/read`, `POST /api/notifications/mark-all-read`. Frontend: bell + unread badge + dropdown panel in the sidebar, plus dedicated `/admin/notifications` and `/rep/notifications` pages with all/unread filters.
- **Auth**: login, /me, logout, forgot/reset password. Bcrypt, JWT, httpOnly cookies + Bearer fallback. Reset flow is tz-aware and invalidates all outstanding tokens on success.
- **Resend email** (`/app/backend/email_service.py`) — 100% env-var driven: `RESEND_API_KEY` + `RESEND_FROM_EMAIL`. Empty key → logs the reset link locally. Set a production key + verified sender at deploy time, no code changes required.
- **Multi-role admins**: `owner` + `admin` + `representative`. Owner-only endpoints under `/api/owner/admins`.
- **Audit log** at `GET /api/admin/audit-log` — every state-changing action recorded.
- **Admin console**: dashboard w/ metrics + revenue chart + top countries; Representatives CRUD w/ suspend + password reset; Banner Inventory (48 countries × 7 regions) CPM editor; TV Projects list with status filter + per-card status dropdown (active/draft/closed); Proposals review; Global Reports; **Audit Log**; **Administrators** (owner-only); **Notifications**.
- **Rep console**: dashboard; **cinematic 2D world map** + region list + per-country impressions override in campaign builder; Campaigns list; TV Sponsorship Catalog + editorial project pages; Sponsorships list; TV proposal submission; Reports; **Notifications**.
- **TV Project status**: draft/active/closed. Reps only see active projects. New sponsorships blocked on non-active projects.
- **Seed data**: 1 owner + 2 sample reps + 48 countries with regional CPM + 3 sample TV projects.

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
1. Run end-to-end testing subagent covering auth + full commercial workflow for both roles.
2. Fix any critical issues surfaced by testing agent.
3. Consider revenue enhancement: exportable "Investment Memorandum" PDF for TV project pages so representatives can share the presentation with clients as a branded proposal.
