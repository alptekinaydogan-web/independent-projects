"""Independent Projects — shared configuration, database, logger, environment."""
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

# ---- Database ----
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ---- Logger ----
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ip")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
