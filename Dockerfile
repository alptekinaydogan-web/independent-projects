# ============================================================================
#  Independent Commerce — production Dockerfile
#
#  Single container running:
#    - nginx (serves the CRA build + reverse-proxies /api → uvicorn)
#    - uvicorn (FastAPI backend on 127.0.0.1:8001)
#    - supervisord (process manager)
#
#  Coolify routes external HTTPS traffic to the container's port 80. No host
#  port is exposed by docker-compose.yml — the reverse proxy handles routing.
# ============================================================================

# ------- Stage 1: build the React frontend -----------------------------------
FROM node:20-alpine AS frontend-build

WORKDIR /build

# Install yarn deps deterministically from the authoritative lockfile
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --non-interactive

# Build the CRA production bundle
COPY frontend/ ./
# Disable the ESLint webpack plugin in CI/production builds so unused-imports
# do not fail the build (they are only a lint concern, not a runtime concern).
ENV CI=true DISABLE_ESLINT_PLUGIN=true
RUN yarn build

# ------- Stage 2: runtime -----------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps: nginx (frontend) + supervisord + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Backend ---
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt
COPY backend/ ./

# --- Frontend static bundle ---
COPY --from=frontend-build /build/build /usr/share/nginx/html

# --- nginx + supervisord config ---
# Remove Debian defaults so they cannot conflict with our configuration.
# The default /etc/supervisor/supervisord.conf ships an [include] directive
# and its own [supervisord]/[unix_http_server]/etc. sections — installing our
# config at that same path (instead of conf.d) prevents duplicate-section
# errors at container start, which surface in Coolify as a CMD failure on
# the last line of the Dockerfile.
RUN rm -f /etc/nginx/conf.d/default.conf /etc/nginx/sites-enabled/default \
    && rm -f /etc/supervisor/supervisord.conf \
    && rm -rf /etc/supervisor/conf.d
COPY deploy/nginx.conf        /etc/nginx/nginx.conf
COPY deploy/supervisord.conf  /etc/supervisor/supervisord.conf

# Runtime dirs required by nginx + supervisord + the FastAPI upload flow.
RUN mkdir -p /var/log/supervisor /var/log/nginx /var/lib/nginx/body /run \
    && chown -R www-data:www-data /var/lib/nginx /var/log/nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://127.0.0.1/api/health > /dev/null || exit 1

# Run supervisord in the foreground so the container stays alive
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf", "-n"]
