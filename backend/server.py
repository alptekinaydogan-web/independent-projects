"""Independent Projects — FastAPI application entrypoint.

Post-cleanup: banner marketplace / inventory / campaigns / sponsorship
proposal routers have been removed. The platform's commercial surface is
now the Project Library (routers/tv.py) with the Apply-to-Produce
workflow, Partner project submissions (routers/proposals.py), and a
future-proof category catalog (routers/categories.py).
"""
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from core import CORS_ORIGINS, client, logger
from storage import init_storage
from seed import run_seed
from background_tasks import drain as drain_background_tasks

# Routers
from routers.auth import router as auth_router
from routers.representatives import router as reps_router
from routers.tv import router as tv_router
from routers.proposals import router as proposals_router
from routers.reports import router as reports_router
from routers.uploads import router as uploads_router
from routers.owner import router as owner_router
from routers.audit_log import router as audit_router
from routers.scheduler_admin import router as scheduler_router
from routers.reference import router as reference_router
from routers.categories import router as categories_router
from notifications import router as notifications_router


app = FastAPI(title="Independent Commerce API")

# All routes under /api
api = APIRouter(prefix="/api")
for r in (auth_router, reps_router,
          tv_router, proposals_router, reports_router,
          uploads_router, owner_router, audit_router, scheduler_router,
          reference_router, categories_router, notifications_router):
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


@app.on_event("shutdown")
async def shutdown():
    await drain_background_tasks(timeout=10.0)
    client.close()
