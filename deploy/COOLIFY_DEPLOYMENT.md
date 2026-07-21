# Independent Commerce — Coolify Deployment Guide

This document is the single source of truth for deploying Independent Commerce
to a Coolify-managed server. It matches the deployment standard already in
production for Independent Media Network, DrPR, PressLab, Independent TV and
Independent Partner.

---

## 1. What ships in the container

A single container running:

| Process       | Port          | Role                                          |
|---------------|---------------|-----------------------------------------------|
| `nginx`       | `:80`         | Serves the CRA build + reverse-proxies `/api` |
| `uvicorn`     | `127.0.0.1:8001` (internal) | Runs the FastAPI backend        |
| `supervisord` | –             | Keeps both processes alive                    |

Coolify's built-in reverse proxy (Traefik) terminates TLS on the public
domain and forwards HTTP to the container's port 80. **No host ports are
mapped.** `docker-compose.yml` uses `expose:` — the way Coolify expects.

---

## 2. Prerequisites

- Coolify instance running (v4+).
- A MongoDB instance reachable from the Coolify network. Either:
  * Deploy the Coolify **MongoDB** service (recommended), or
  * Use a managed MongoDB Atlas cluster and its connection URI.

---

## 3. Deployment steps

### 3.1. Create the resource

1. In Coolify → **Resources** → **New** → **Application**.
2. Source: **GitHub** → select this repository, branch `main`.
3. Build pack: **Docker Compose** (Coolify will auto-detect
   `docker-compose.yml`).
4. Domain: enter the production hostname (e.g.
   `commerce.independentmedia.hub`). Coolify handles the TLS certificate
   through Let's Encrypt automatically.

### 3.2. Environment variables

Paste the following into Coolify → the app → **Environment** tab. Values
in `< >` must be replaced. Use `.env.example` as a checklist.

| Variable            | Required | Notes                                                       |
|---------------------|----------|-------------------------------------------------------------|
| `MONGO_URL`         | yes      | Full MongoDB URI (e.g. `mongodb://mongo:27017`)             |
| `DB_NAME`           | yes      | Recommended: `independent_commerce`                         |
| `JWT_SECRET`        | yes      | 32+ random bytes                                            |
| `ADMIN_EMAIL`       | yes      | Root administrator email                                    |
| `ADMIN_PASSWORD`    | yes      | Root administrator password                                 |
| `FRONTEND_URL`      | yes      | `https://<your-domain>` — used in outgoing emails           |
| `CORS_ORIGINS`      | yes      | `https://<your-domain>`                                     |
| `RESEND_API_KEY`    | no       | Empty ⇒ password-reset emails logged, not sent              |
| `RESEND_FROM_EMAIL` | no       | Default `onboarding@resend.dev`                             |
| `EMERGENT_LLM_KEY`  | no       | Only if LLM features are used                               |

### 3.3. Deploy

1. Click **Deploy**. Coolify builds the image with the committed
   `Dockerfile`, tags it `independent-commerce:latest`, and boots the
   container.
2. The `HEALTHCHECK` polls `/docs` — Coolify waits for the first healthy
   probe before flipping traffic.
3. On first boot the backend seeds the owner user, the default `tv_formats`
   category and three demo TV projects. Login with `ADMIN_EMAIL` /
   `ADMIN_PASSWORD`.

### 3.4. Zero-downtime rollout

Coolify uses the standard rolling strategy — the new container is built and
health-checked before the previous one is stopped. No manual traffic switch
is required.

---

## 4. Rules

- **No host port mapping.** `docker-compose.yml` must only `expose:` port 80.
- **No secrets in git.** `.env` is `.dockerignore`d and `.gitignore`d.
- **CI must be green.** `.github/workflows/ci.yml` gates every deploy —
  Coolify redeploys are performed only from commits on `main` where CI
  passed. This mirrors the rule in `docs/CI_PIPELINE.md`.
- **Yarn is the frontend package manager.** The Dockerfile installs with
  `yarn install --frozen-lockfile`. `package-lock.json` is not present and
  must not be added.
- **Python 3.11.** Backend requirements are locked in
  `backend/requirements.txt`.

---

## 5. Rolling back

1. Coolify → the app → **Deployments** tab.
2. Locate the last known-good deployment and click **Redeploy**.
3. Rollback re-runs the same image build for that commit; database data is
   preserved.

---

## 6. Local production build (verification only)

To reproduce the Coolify build locally on any machine with Docker:

```bash
cp .env.example .env       # then edit .env with real values
docker compose build       # builds the image
docker compose up -d       # runs it (container listens on port 80)
docker compose logs -f app # tail logs
```

Once verified, `docker compose down` and push to `main`. Coolify performs
the same build server-side.

---

## 7. Troubleshooting

| Symptom                                     | Where to look                                            |
|---------------------------------------------|----------------------------------------------------------|
| 502 on `/api/*`                             | `docker compose logs app` — search `backend.stderr.log`  |
| Frontend loads but API 500s                 | `MONGO_URL` unreachable or auth invalid                  |
| Login fails on first deploy                 | `ADMIN_EMAIL` / `ADMIN_PASSWORD` typo — reset via env    |
| SSL certificate not issuing                 | Coolify → Proxy tab → check Traefik logs                 |
| Password-reset emails not delivered         | `RESEND_API_KEY` empty ⇒ falls back to log-only          |
| Container flapping Healthy ⇄ Unhealthy      | See §7.1 below                                            |

### 7.1. Container flapping between Healthy and Unhealthy

The Docker `HEALTHCHECK` polls `http://127.0.0.1/healthz`, which is served
**by nginx directly** (no upstream call). So the container is considered
healthy as soon as nginx is listening on `:80`. If it still flaps:

1. **Env vars missing.** The backend fails fast on `KeyError` for
   `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.
   Supervisord restarts uvicorn in a loop; nginx stays up so `/healthz`
   still returns 200 — but `/api/health` returns 502. Confirm every
   required var in Coolify → Environment.
2. **MongoDB unreachable.** Backend logs will show `ServerSelectionTimeoutError`.
   Verify `MONGO_URL` uses the Coolify network hostname (not `localhost`).
3. **OOM.** `docker compose stats` shows memory pegged at 100%. Reduce
   uvicorn workers (already 1) or increase the Coolify server RAM.
4. **Coolify proxy misrouted.** Check Coolify → the app → **Proxy** tab
   and confirm the domain maps to port 80 of the container.

To inspect a live container:
```bash
docker compose exec app sh
supervisorctl status              # both processes RUNNING?
tail -f /var/log/supervisor/backend.stderr.log
tail -f /var/log/nginx/error.log
curl -v http://127.0.0.1/healthz  # nginx-served (always 200)
curl -v http://127.0.0.1/api/health  # backend-served (200 when uvicorn is up)
```

---

## 8. Post-deployment smoke test

After Coolify reports the deployment healthy:

1. Open `https://<domain>` — the browser tab must display
   **Independent Commerce**.
2. Login as owner with `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
3. Navigate to **Project Library** → open any project → verify the modular
   Project Page renders (Hero + Executive Summary + Format + Sponsorship +
   Tech Specs + Brand + Downloads).
4. Login as a representative → open **Browse Projects** → open a project →
   submit an **Apply to Produce** request.
5. Back in the admin console, open **Applications Review** and approve the
   request.

If all five pass, the deployment is production-ready.
