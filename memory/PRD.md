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
- **Auth**: login, /me, logout, forgot/reset password. Bcrypt, JWT (8h access + 7d refresh), httpOnly SameSite=None cookies + Bearer header. Password reset uses timezone-aware token expiry check and invalidates all outstanding tokens on successful reset.
- **Resend email integration** (`/app/backend/server.py::send_password_reset_email`) — configurable via `RESEND_API_KEY` and `RESEND_FROM_EMAIL` env vars. Falls back to logging the link when key is empty (sandbox mode).
- **Multi-role admins**: `owner` (root, seeded, manages other admins) + `admin` (full access minus admin management) + `representative`. Owner-only endpoints: `GET/POST/DELETE /api/owner/admins`.
- **Audit log**: All state-changing actions written to `db.audit_log` via `audit()` helper. Endpoint `GET /api/admin/audit-log?entity_type=&actor_role=&limit=`. Frontend at `/admin/audit-log`.
- **Admin console**: dashboard w/ metrics + revenue chart + top countries; Representatives CRUD w/ suspend + password reset; Banner Inventory (48 countries × 7 regions) CPM editor; TV Projects list with **status filter (all/active/draft/closed)** and **per-card status dropdown** (Set active / Draft / Close); Proposals review; Global Reports; **Audit Log**; **Administrators** (owner-only).
- **Rep console**: dashboard w/ revenue metrics + featured TV; Banner Campaign Builder with **cinematic 2D world map** (react-simple-maps + d3-geo, world-atlas topojson) + **region-list tab** + **per-country impressions override panel**; Campaign list; TV Sponsorship Catalog + Editorial project page w/ hero + demo video modal + episode grid picker + sticky sponsorship checkout; Sponsorships list; Submit TV Proposal + track status; Rep Reports.
- **TV Project status**: draft/active/closed. Reps only see active projects. Admins can quick-toggle status.
- **Seed data**: 1 owner + 2 sample representatives (FR, GB) + 48 countries with regional default CPM + 3 sample TV projects.

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
