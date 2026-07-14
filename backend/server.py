"""Independent Media Hub — FastAPI application entrypoint.

Assembles routers, configures CORS, runs startup seeding.
Individual endpoint logic lives in /app/backend/routers/*.
"""
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from core import CORS_ORIGINS, client, logger
from storage import init_storage
from seed import run_seed
from scheduler import start_scheduler, run_once

# Routers
from routers.auth import router as auth_router
from routers.countries import router as countries_router
from routers.representatives import router as reps_router
from routers.inventory import router as inventory_router
from routers.campaigns import router as campaigns_router
from routers.tv import router as tv_router
from routers.proposals import router as proposals_router
from routers.reports import router as reports_router
from routers.uploads import router as uploads_router
from routers.owner import router as owner_router
from routers.audit_log import router as audit_router
from routers.scheduler_admin import router as scheduler_router
from notifications import router as notifications_router


app = FastAPI(title="Independent Media Hub API")

# All routes under /api
api = APIRouter(prefix="/api")
for r in (auth_router, countries_router, reps_router, inventory_router,
          campaigns_router, tv_router, proposals_router, reports_router,
          uploads_router, owner_router, audit_router, scheduler_router,
          notifications_router):
    api.include_router(r)
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.warning(f"Storage init failed (uploads disabled until fixed): {e}")
    await run_seed()
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    client.close()
