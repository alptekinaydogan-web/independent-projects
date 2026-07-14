"""Independent Media Hub — shared configuration, database, logger, environment."""
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

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
APP_NAME = os.environ.get("APP_NAME", "independent-media-hub")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
CAMPAIGN_REMINDER_DAYS = sorted({
    int(x.strip()) for x in os.environ.get("CAMPAIGN_REMINDER_DAYS", "30,14,7,1").split(",")
    if x.strip().isdigit()
}, reverse=True) or [30, 14, 7, 1]
try:
    PROPOSAL_ARCHIVE_DAYS = int(os.environ.get("PROPOSAL_ARCHIVE_DAYS", "90"))
except ValueError:
    PROPOSAL_ARCHIVE_DAYS = 90
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

# ---- Constants ----
ADMIN_ROLES = {"owner", "admin"}
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"

# ---- Database ----
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ---- Logger ----
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("imh")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
