"""Startup seeding — idempotent. Now uses the network×position inventory catalog.
Legacy campaigns/sponsorships are migrated to the proposal workflow (approved status
preserved so already-booked work stays visible)."""
import uuid
from pathlib import Path
from core import db, now_iso, ADMIN_EMAIL, ADMIN_PASSWORD, logger
from security import hash_password, verify_password
from networks_data import all_inventory


async def create_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.campaigns.create_index("rep_id")
    await db.campaigns.create_index("status")
    await db.tv_projects.create_index("id", unique=True)
    await db.sponsorships.create_index("rep_id")
    await db.sponsorships.create_index("tv_project_id")
    await db.sponsorships.create_index("status")
    await db.proposals.create_index("rep_id")
    await db.audit_log.create_index([("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await db.notifications.create_index([("user_id", 1), ("read", 1)])
    await db.notifications.create_index([("event_type", 1), ("entity_id", 1)])
    await db.campaigns.create_index("end_date")
    await db.notifications.update_many({"severity": {"$exists": False}}, {"$set": {"severity": "info"}})
    await db.notifications.update_many({"archived": {"$exists": False}}, {"$set": {"archived": False}})


async def migrate_legacy_data() -> None:
    """Migrate iteration_1..5 data into the new proposal schema.

    - old campaigns.status='confirmed' -> 'approved'
    - drop revenue/margin/cost fields
    - infer network/position from first available inventory item (Global Hero)
    - old sponsorships.status='confirmed' -> 'approved'
    """
    inv = all_inventory()
    default_inv = next((i for i in inv if i["network_key"] == "global" and i["position_key"] == "hero"),
                       inv[0])

    async for c in db.campaigns.find({"status": "confirmed"}):
        upd = {"status": "approved", "decided_at": c.get("created_at", now_iso())}
        if "network_key" not in c:
            upd.update({
                "inventory_id": default_inv["id"],
                "network_key": default_inv["network_key"],
                "network_name": default_inv["network_name"],
                "position_key": default_inv["position_key"],
                "position_name": default_inv["position_name"],
            })
        if "offer_amount_usd" not in c:
            upd["offer_amount_usd"] = c.get("client_total_price_usd") or 0
        if "client_reference" not in c:
            upd["client_reference"] = c.get("client_name", "")
        await db.campaigns.update_one({"id": c["id"]},
                                       {"$set": upd,
                                        "$unset": {"per_country": "", "internal_cost_usd": "",
                                                   "client_total_price_usd": "", "margin_usd": "",
                                                   "total_impressions": ""}})

    async for s in db.sponsorships.find({"status": "confirmed"}):
        upd = {"status": "approved", "decided_at": s.get("created_at", now_iso())}
        if "offer_amount_usd" not in s:
            upd["offer_amount_usd"] = s.get("client_total_price_usd") or 0
        if "client_reference" not in s:
            upd["client_reference"] = s.get("client_name", "")
        if "proposal_name" not in s:
            upd["proposal_name"] = s.get("tv_project_title", "")
        await db.sponsorships.update_one({"id": s["id"]},
                                          {"$set": upd,
                                           "$unset": {"internal_cost_usd": "",
                                                      "client_total_price_usd": "", "margin_usd": ""}})

    # Drop the legacy country-based banner_inventory collection — no longer used
    if "banner_inventory" in await db.list_collection_names():
        await db.banner_inventory.drop()

    # Remove TV project fixed-price fields
    await db.tv_projects.update_many({"price_per_episode_usd": {"$exists": True}},
                                      {"$unset": {"price_per_episode_usd": ""}})


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
    """The QA/demo environment operates with a single licensed representative
    (Victor Laurent · Paris Media Group). A second rep record (Amelia Hart)
    exists historically — we keep the row for referential integrity but mark
    it inactive so the platform behaves as a one-representative environment
    during the QA phase.
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
        s["id"] = str(uuid.uuid4()); s["created_at"] = now_iso()
        await db.tv_projects.insert_one(s)


def write_credentials_file() -> None:
    creds_dir = Path("/app/memory")
    creds_dir.mkdir(exist_ok=True)
    (creds_dir / "test_credentials.md").write_text(f"""# Independent Commerce – Test Credentials

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
    await create_indexes()
    await migrate_legacy_data()
    await seed_owner()
    await seed_reps()
    await seed_tv_projects()
    write_credentials_file()
