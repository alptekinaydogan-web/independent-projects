"""Startup seeding — idempotent. Creates the owner, sample reps, banner inventory,
sample TV projects, and writes test_credentials.md."""
import uuid
from pathlib import Path
from core import db, now_iso, ADMIN_EMAIL, ADMIN_PASSWORD, logger
from security import hash_password, verify_password
from countries_data import COUNTRIES, DEFAULT_PRICES


async def create_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.banner_inventory.create_index("country_code", unique=True)
    await db.campaigns.create_index("rep_id")
    await db.tv_projects.create_index("id", unique=True)
    await db.sponsorships.create_index("rep_id")
    await db.sponsorships.create_index("tv_project_id")
    await db.proposals.create_index("rep_id")
    await db.audit_log.create_index([("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("read", 1)])
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)


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
    samples = [
        {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!",
         "name": "Victor Laurent", "agency_name": "Paris Media Group", "country": "FR"},
        {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!",
         "name": "Amelia Hart", "agency_name": "London House Media", "country": "GB"},
    ]
    for r in samples:
        if not await db.users.find_one({"email": r["email"]}):
            await db.users.insert_one({
                "id": str(uuid.uuid4()), "email": r["email"],
                "password_hash": hash_password(r["password"]),
                "name": r["name"], "role": "representative",
                "agency_name": r["agency_name"], "country": r["country"],
                "is_active": True, "created_at": now_iso(),
            })


async def seed_inventory() -> None:
    if await db.banner_inventory.count_documents({}) > 0:
        return
    for code, name, region in COUNTRIES:
        await db.banner_inventory.insert_one({
            "country_code": code, "country_name": name, "region": region,
            "price_cpm_usd": DEFAULT_PRICES[region],
            "min_impressions": 10000, "updated_at": now_iso(),
        })


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
            "total_episodes": 100, "price_per_episode_usd": 300,
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
            "total_episodes": 24, "price_per_episode_usd": 900,
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
            "total_episodes": 12, "price_per_episode_usd": 1800,
            "sponsorship_rights": "Full episode presenting sponsor. Two dedicated spots. Digital rights included.",
            "status": "active",
        },
    ]
    for s in samples:
        s["id"] = str(uuid.uuid4()); s["created_at"] = now_iso()
        await db.tv_projects.insert_one(s)


def write_credentials_file() -> None:
    creds_dir = Path("/app/memory")
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / "test_credentials.md").write_text(f"""# Independent Media Hub – Test Credentials

## Owner (root administrator)
- Email: `{ADMIN_EMAIL}`
- Password: `{ADMIN_PASSWORD}`
- Role: `owner` (can create/remove admins, full access)

## Representative accounts
- Email: `victor.laurent@parismedia.fr`  Password: `Rep2026!`  Agency: Paris Media Group (FR)
- Email: `amelia.hart@londonhouse.co.uk`  Password: `Rep2026!`  Agency: London House Media (GB)

## Auth endpoints
- POST /api/auth/login  {{ email, password }}
- POST /api/auth/logout
- GET  /api/auth/me
- POST /api/auth/forgot-password
- POST /api/auth/reset-password

## Roles
- `owner`  — root administrator, seeded once, can create/remove `admin` accounts (POST/DELETE /api/owner/admins)
- `admin`  — full administrator access except managing other admins
- `representative` — licensed commercial partner
""")


async def run_seed() -> None:
    await create_indexes()
    await seed_owner()
    await seed_reps()
    await seed_inventory()
    await seed_tv_projects()
    write_credentials_file()
