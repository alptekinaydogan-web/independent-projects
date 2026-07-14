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
- **Commercial model = negotiated commercial proposals**. There are no fixed prices, no internal costs, no representative revenue, no margin, no client price anywhere in the platform. Representatives negotiate with their customers OFF-platform, then submit a confidential commercial proposal to Independent Media Network. Administrators approve / reject / request revision. Proposals are private per representative — reps never see each other's offers.
- **Inventory = network × position catalog**. 9 networks (Global + Tourism, Health, Real Estate, Education, Economy, Sports, Technology, Entertainment) × 10 standardized positions (Hero, Header, Sidebar Top/Bottom, Article Top/Middle/Bottom, Footer, Mobile, Sticky) = 90 products. Each product spans the entire network automatically; adding country sites does not require any UI change.
- **Two commercial modules, both proposal-based**: Banner Proposals and TV Sponsorship Proposals. Each has `pending_review → approved / rejected / revision_requested` lifecycle with admin decision endpoint + confidential notes.
- **Notification Center** — role-aware, categorized (`action_required`, `reminder`, `info`), soft-delete archive, dashboard "Needs your attention" strip, per-severity bell badge color, `campaign.expiring.30d/14d/7d/1d` reminders via background scheduler.
- **Operational reports & dashboards** — proposal counts by status, monthly submitted/approved trend, top networks purchased, inventory product count, active reps. Zero revenue metrics displayed.
- **Auth**: JWT + bcrypt + Resend-driven password reset (env-driven RESEND_API_KEY + RESEND_FROM_EMAIL).
- **Modular backend**: `server.py` orchestrator + `core / security / models / audit_helper / email_service / storage / notifications / networks_data / scheduler / seed / routers/*`.
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
1. Run end-to-end testing subagent covering auth + full commercial workflow for both roles.
2. Fix any critical issues surfaced by testing agent.
3. Consider revenue enhancement: exportable "Investment Memorandum" PDF for TV project pages so representatives can share the presentation with clients as a branded proposal.
