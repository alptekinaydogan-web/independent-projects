"""Startup seeding — idempotent.

Post-cleanup: banner marketplace / inventory / campaigns / sponsorships
migrations have been removed. Legacy collections are dropped on startup
so the platform runs on a clean data model focused on the Project Library.
"""
import uuid
from pathlib import Path
from core import db, now_iso, ADMIN_EMAIL, ADMIN_PASSWORD, DEFAULT_CATEGORY_SLUG, logger
from security import hash_password, verify_password


LEGACY_COLLECTIONS = (
    "campaigns", "sponsorships", "banner_inventory",
)


async def create_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.categories.create_index("slug", unique=True)
    await db.tv_projects.create_index("id", unique=True)
    await db.tv_projects.create_index("category_slug")
    await db.tv_projects.create_index("status")
    await db.productions.create_index([("tv_project_id", 1), ("rep_id", 1)])
    await db.productions.create_index("status")
    await db.tv_projects.create_index("source")
    await db.tv_projects.create_index("moderation_status")
    await db.tv_projects.create_index("submitted_by_rep_id")
    await db.audit_log.create_index([("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("read", 1)])
    await db.notifications.create_index([("event_type", 1), ("entity_id", 1)])
    await db.notifications.update_many({"severity": {"$exists": False}}, {"$set": {"severity": "info"}})
    await db.notifications.update_many({"archived": {"$exists": False}}, {"$set": {"archived": False}})


async def drop_legacy_collections() -> None:
    """Remove banner marketplace legacy collections that are no longer used."""
    existing = await db.list_collection_names()
    for name in LEGACY_COLLECTIONS:
        if name in existing:
            await db[name].drop()
            logger.info(f"dropped legacy collection: {name}")


async def seed_categories() -> None:
    """Seed the default `tv_formats` category so TV projects have a
    referential parent. Future categories are added by inserting new
    documents into `categories` — no code change required.
    """
    if await db.categories.find_one({"slug": DEFAULT_CATEGORY_SLUG}):
        return
    await db.categories.insert_one({
        "id": str(uuid.uuid4()),
        "slug": DEFAULT_CATEGORY_SLUG,
        "name": "TV Formats",
        "description": ("Original television formats — series, documentaries "
                         "and interview programs designed for country partner "
                         "production under the Independent Projects standard."),
        "order": 1,
        "is_active": True,
        "created_at": now_iso(),
    })
    logger.info(f"seeded default category: {DEFAULT_CATEGORY_SLUG}")


async def normalise_tv_projects() -> None:
    """Backfill category_slug + source/moderation_status/published on any
    existing TV project document."""
    await db.tv_projects.update_many(
        {"category_slug": {"$exists": False}},
        [{"$set": {"category_slug": {"$ifNull": ["$category", DEFAULT_CATEGORY_SLUG]}}}]
    )
    await db.tv_projects.update_many(
        {"category": {"$exists": False}},
        [{"$set": {"category": {"$ifNull": ["$category_slug", DEFAULT_CATEGORY_SLUG]}}}]
    )
    # Unified moderation fields — anything pre-existing is treated as an
    # approved Official Project so it stays visible in the Library.
    await db.tv_projects.update_many({"source":            {"$exists": False}}, {"$set": {"source":            "admin"}})
    await db.tv_projects.update_many({"moderation_status": {"$exists": False}}, {"$set": {"moderation_status": "approved"}})
    await db.tv_projects.update_many({"published":         {"$exists": False}}, {"$set": {"published": True}})
    await db.tv_projects.update_many({"featured":          {"$exists": False}}, {"$set": {"featured": False}})
    await db.tv_projects.update_many({"archived":          {"$exists": False}}, {"$set": {"archived": False}})
    await db.tv_projects.update_many({"revision_history":  {"$exists": False}}, {"$set": {"revision_history": []}})
    await db.tv_projects.update_many({"download_assets":   {"$exists": False}}, {"$set": {"download_assets": []}})


async def migrate_proposals_to_projects() -> None:
    """Absorb the legacy `proposals` collection into unified `tv_projects`.

    Each legacy proposal document becomes a partner-sourced project with
    the same id (so notification / audit links remain valid). The
    `proposals` collection is dropped afterwards.
    """
    if "proposals" not in await db.list_collection_names():
        return
    async for old in db.proposals.find({}):
        if not old.get("id"):
            continue
        # Skip if already migrated
        if await db.tv_projects.find_one({"id": old["id"]}):
            continue
        legacy_status = old.get("status", "in_review")
        moderation = {
            "approved": "approved", "rejected": "rejected",
        }.get(legacy_status, "submitted")
        published = moderation == "approved"
        doc = {
            "id": old["id"],
            "title": old.get("title", "Untitled"),
            "subtitle": "", "tagline": "",
            "overview": old.get("description", ""),
            "synopsis": old.get("description", ""),
            "concept": "",
            "production_format": old.get("format", "documentary"),
            "total_episodes": int(old.get("estimated_episodes") or 0),
            "category_slug": DEFAULT_CATEGORY_SLUG,
            "category": DEFAULT_CATEGORY_SLUG,
            "status": "active" if published else "draft",
            "hero_image_url": "", "demo_video_url": "",
            "languages": [],
            "sponsorship_opportunities": [],
            "download_assets": [],
            "source": "partner",
            "moderation_status": moderation,
            "published": published, "featured": False, "archived": False,
            "admin_feedback": old.get("admin_notes", ""),
            "internal_notes": "",
            "revision_history": [],
            "submitted_by_rep_id":   old.get("rep_id"),
            "submitted_by_rep_name": old.get("rep_name"),
            "submitted_by_agency":   old.get("agency_name", ""),
            "submitted_by_country":  old.get("country", ""),
            "submitted_at": old.get("created_at", ""),
            "decided_at":   old.get("decided_at", ""),
            "created_at":   old.get("created_at", now_iso()),
        }
        await db.tv_projects.insert_one(doc)
    await db.proposals.drop()
    logger.info("migrated legacy `proposals` collection into unified tv_projects (source=partner)")


async def seed_owner() -> None:
    email = ADMIN_EMAIL.lower()
    existing = await db.users.find_one({"email": email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": email,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Platform Owner", "role": "owner",
            "is_active": True, "created_at": now_iso(),
        })
        logger.info(f"Seeded owner {email}")
    else:
        updates = {}
        if not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
            updates["password_hash"] = hash_password(ADMIN_PASSWORD)
        if existing.get("role") == "admin":
            updates["role"] = "owner"
            updates["name"] = existing.get("name") or "Platform Owner"
        if updates:
            await db.users.update_one({"email": email}, {"$set": updates})


async def seed_reps() -> None:
    """The QA environment operates with a single licensed representative
    (Victor Laurent · Paris Media Group). A second historical record is
    preserved but marked inactive so the platform behaves as a
    one-representative environment during QA.
    """
    samples = [
        {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!",
         "name": "Victor Laurent", "agency_name": "Paris Media Group", "country": "FR",
         "is_active": True},
        {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!",
         "name": "Amelia Hart", "agency_name": "London House Media", "country": "GB",
         "is_active": False},
    ]
    for r in samples:
        if not await db.users.find_one({"email": r["email"]}):
            await db.users.insert_one({
                "id": str(uuid.uuid4()), "email": r["email"],
                "password_hash": hash_password(r["password"]),
                "name": r["name"], "role": "representative",
                "agency_name": r["agency_name"], "country": r["country"],
                "is_active": r["is_active"], "created_at": now_iso(),
            })
        else:
            await db.users.update_one({"email": r["email"]},
                                       {"$set": {"is_active": r["is_active"]}})


async def seed_tv_projects() -> None:
    if await db.tv_projects.count_documents({}) > 0:
        return
    samples = [
        {
            "title": "World of Girls",
            "tagline": "A global journey through the lives, dreams and challenges of young women.",
            "synopsis": "A 100-episode documentary series filmed across 40 countries, portraying the diverse realities of young women in 2026. Each episode is a self-contained story with cinematic production values.",
            "hero_image_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600",
            "demo_video_url": "",
            "target_audience": "Adults 25-54, socially engaged, culturally curious",
            "distribution": "Independent TV + national broadcast partners in 40 countries",
            "languages": ["English", "French", "Spanish", "Arabic", "Mandarin"],
            "total_episodes": 100,
            "sponsorship_rights": "Opening credit, closing credit, one 15s sponsor spot mid-roll, digital pre-roll on VOD.",
            "status": "active",
        },
        {
            "title": "The Investigators",
            "tagline": "An interview series with the world's most fearless investigative journalists.",
            "synopsis": "24 in-depth interviews. One journalist per episode. Deep, unhurried, editorial conversations that let the story breathe.",
            "hero_image_url": "https://images.unsplash.com/photo-1640130541949-aa5d40f9635d?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600",
            "demo_video_url": "",
            "target_audience": "Executives, policy makers, cultural elite",
            "distribution": "Independent TV, YouTube, curated syndication",
            "languages": ["English"],
            "total_episodes": 24,
            "sponsorship_rights": "Presenting sponsor billing, one dedicated 30s spot, logo integration.",
            "status": "active",
        },
        {
            "title": "Silent Continents",
            "tagline": "A cinematic exploration of the natural landscapes that shape our planet.",
            "synopsis": "12 episodes. Aerial cinematography, immersive sound design, and slow storytelling across six continents.",
            "hero_image_url": "https://images.unsplash.com/photo-1760637627433-e7de199a8243?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600",
            "demo_video_url": "",
            "target_audience": "Nature enthusiasts, families, premium travel audiences",
            "distribution": "Independent TV Global + airline in-flight partners",
            "languages": ["English", "German", "Japanese"],
            "total_episodes": 12,
            "sponsorship_rights": "Full episode presenting sponsor. Two dedicated spots. Digital rights included.",
            "status": "active",
        },
    ]
    for s in samples:
        s["id"] = str(uuid.uuid4())
        s["created_at"] = now_iso()
        s["category_slug"] = DEFAULT_CATEGORY_SLUG
        s["category"] = DEFAULT_CATEGORY_SLUG  # legacy mirror
        # Unified project envelope
        s["source"] = "admin"
        s["moderation_status"] = "approved"
        s["published"] = True
        s["featured"] = s.get("featured", False)
        s["archived"] = False
        s["revision_history"] = []
        s["download_assets"] = s.get("download_assets", [])
        s["overview"] = s.get("overview", s.get("synopsis", ""))
        await db.tv_projects.insert_one(s)


def write_credentials_file() -> None:
    creds_dir = Path("/app/memory")
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / "test_credentials.md").write_text(f"""# Independent Projects – Test Credentials

## Owner (root administrator)
- Email: `{ADMIN_EMAIL}`
- Password: `{ADMIN_PASSWORD}`
- Role: `owner`

## Representative account (QA phase — single licensed representative)
- Email: `victor.laurent@parismedia.fr`  Password: `Rep2026!`  Agency: Paris Media Group (FR)

## Legacy accounts (kept inactive for referential integrity)
- Email: `amelia.hart@londonhouse.co.uk`  Password: `Rep2026!`  Status: **inactive**
""")


async def run_seed() -> None:
    await drop_legacy_collections()
    await create_indexes()
    await seed_categories()
    await normalise_tv_projects()
    await migrate_proposals_to_projects()
    await seed_owner()
    await seed_reps()
    await seed_tv_projects()
    write_credentials_file()
