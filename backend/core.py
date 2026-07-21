"""Independent Projects — shared configuration, database, logger, environment."""
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ---- Environment (fail-fast on required) ----
JWT_SECRET = os.environ["JWT_SECRET"]
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").rstrip("/")
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = os.environ.get("APP_NAME", "independent-projects")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

# ---- Constants ----
ADMIN_ROLES = {"owner", "admin"}
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"

# Default category slug seeded on startup. Additional categories can be
# introduced without any schema change — they simply become new documents in
# the `categories` collection.
DEFAULT_CATEGORY_SLUG = "tv_formats"

# ---- Logger (created early so module-level import failures are visible) ----
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ip")


# ---- Database (LAZY INITIALIZATION) ----
# CRITICAL: `AsyncIOMotorClient(MONGO_URL)` used to be called at module
# import time. For `mongodb+srv://` URIs pymongo performs a *synchronous*
# SRV DNS lookup inside `__init__`. If DNS is slow, blocked, or the
# cluster is unreachable from the container network (a very common
# Coolify scenario when MONGO_URL points to Atlas and the DNS resolver
# lags), the import hangs *forever* — supervisor reports the uvicorn
# process as RUNNING but it never binds a port and produces no logs
# because it hasn't finished importing `server.py`.
#
# Deferring instantiation to first use decouples container liveness
# from MongoDB reachability. Uvicorn now always boots and serves the
# health endpoints; only routes that actually touch the DB will fail
# (with a fast, explicit error) if Mongo is unreachable.
_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        logger.info("Instantiating Motor client (lazy) …")
        # Fast-fail Mongo operations instead of hanging: 5s to select a
        # server, 5s to open a TCP connection.
        _client = AsyncIOMotorClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=20000,
        )
        logger.info("Motor client ready")
    return _client


class _LazyDBProxy:
    """Attribute + item access proxy that resolves to the real Motor
    database on first use. Lets existing call-sites keep the ergonomic
    `from core import db; db.users.find_one(...)` API without triggering
    a network lookup at import time.
    """

    def _resolve(self) -> AsyncIOMotorDatabase:
        global _db
        if _db is None:
            _db = _get_client()[DB_NAME]
        return _db

    def __getattr__(self, item):
        return getattr(self._resolve(), item)

    def __getitem__(self, item):
        return self._resolve()[item]


db = _LazyDBProxy()


# `client` is imported by server.py for graceful shutdown. Return a
# proxy object that supports `.close()` without instantiating the real
# client if it was never needed.
class _LazyClientProxy:
    def close(self):
        global _client
        if _client is not None:
            _client.close()

    def __getattr__(self, item):
        return getattr(_get_client(), item)


client = _LazyClientProxy()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
