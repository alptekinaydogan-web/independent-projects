"""Background scheduler: campaign expiration reminders + proposal auto-archive.

Runs an hourly loop on the FastAPI event loop. For every campaign with an
end_date, checks whether `days_left` equals one of the configured reminder
thresholds (default 30/14/7/1) and, if we have not already emitted that
specific reminder for the campaign, notifies the owning representative and
all administrators. Also emits a `campaign.expired` reminder the day after
the campaign ends (once).

Additionally, once per day, sweeps proposals whose commercial lifecycle is
complete and archives anything older than the retention window
(`PROPOSAL_ARCHIVE_DAYS`, default 90). Archived proposals remain searchable
by admins but are hidden from operational lists.

Configuration:
    CAMPAIGN_REMINDER_DAYS  — comma-separated days (default "30,14,7,1")
    PROPOSAL_ARCHIVE_DAYS   — days after campaign end / decision (default 90)
"""
import asyncio
from datetime import datetime, timezone, timedelta
from core import db, logger, CAMPAIGN_REMINDER_DAYS, PROPOSAL_ARCHIVE_DAYS, now_iso
from notifications import notify, notify_all_admins
from proposal_history import history_entry

CHECK_INTERVAL_SECONDS = 3600  # every hour


def _parse_iso_date(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date() if "T" in s else datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


async def _has_prior(user_id: str, event_type: str, campaign_id: str) -> bool:
    return await db.notifications.find_one({
        "user_id": user_id, "event_type": event_type, "entity_id": campaign_id,
    }) is not None


async def _emit_campaign_reminders() -> None:
    today = datetime.now(timezone.utc).date()
    campaigns = await db.campaigns.find({"end_date": {"$nin": [None, ""]}}).to_list(5000)
    emitted = 0

    for c in campaigns:
        end_d = _parse_iso_date(c.get("end_date"))
        if not end_d:
            continue
        days_left = (end_d - today).days
        rep_id = c.get("rep_id")
        name = c.get("campaign_name", "Untitled campaign")
        client = c.get("client_name", "your client")
        countries = len(c.get("country_codes", []) or [])

        # Threshold reminders (only when there is a future end)
        if days_left >= 0:
            for threshold in CAMPAIGN_REMINDER_DAYS:
                if days_left != threshold:
                    continue
                event = f"campaign.expiring.{threshold}d"
                if rep_id and not await _has_prior(rep_id, event, c["id"]):
                    plural = "" if threshold == 1 else "s"
                    await notify(
                        [rep_id],
                        event_type=event,
                        title=f"Campaign expires in {threshold} day{plural} · {name}",
                        message=(f"Your campaign for {client} across {countries} countries ends on "
                                 f"{c['end_date'][:10]}. Reach out to renew or extend before it goes dark."),
                        entity_type="campaign", entity_id=c["id"],
                        link="/rep/banners",
                        severity="reminder",
                    )
                    emitted += 1

                # Also alert admins on the 7 and 1 day thresholds — actionable visibility
                if threshold in (7, 1):
                    admin_event = f"campaign.expiring.admin.{threshold}d"
                    if await db.notifications.find_one({"event_type": admin_event, "entity_id": c["id"]}) is None:
                        await notify_all_admins(
                            event_type=admin_event,
                            title=f"Campaign expiring in {threshold} day{plural} · {name}",
                            message=(f"{c.get('agency_name') or c.get('rep_name', 'A representative')} has "
                                     f"a campaign for {client} ending {c['end_date'][:10]}."),
                            entity_type="campaign", entity_id=c["id"],
                            link="/admin/reports",
                            severity="reminder",
                        )
                        emitted += 1

        # Expired — fire once the day after end_date
        if days_left == -1:
            event = "campaign.expired"
            if rep_id and not await _has_prior(rep_id, event, c["id"]):
                await notify(
                    [rep_id],
                    event_type=event,
                    title=f"Campaign expired · {name}",
                    message=(f"Your campaign for {client} ended on {c['end_date'][:10]}. "
                             "Consider following up to renew or upsell."),
                    entity_type="campaign", entity_id=c["id"],
                    link="/rep/banners",
                    severity="reminder",
                )
                emitted += 1

    if emitted:
        logger.info(f"campaign scheduler emitted {emitted} reminder notification(s)")


SYSTEM_ACTOR = {"id": "system", "name": "System auto-archive", "role": "system"}


async def _auto_archive_proposals() -> None:
    """Archive proposals whose commercial lifecycle finished more than
    PROPOSAL_ARCHIVE_DAYS ago. For banners we use end_date if present,
    otherwise decided_at. For sponsorships we use decided_at."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=PROPOSAL_ARCHIVE_DAYS)).isoformat()
    today = datetime.now(timezone.utc).date()
    archived = 0

    async for c in db.campaigns.find({"is_archived": {"$ne": True},
                                      "status": {"$in": ["approved", "rejected"]}}):
        end_raw = c.get("end_date") or ""
        eligible = False
        if end_raw:
            try:
                ed = datetime.strptime(end_raw[:10], "%Y-%m-%d").date()
                if (today - ed).days >= PROPOSAL_ARCHIVE_DAYS:
                    eligible = True
            except Exception:
                pass
        elif c.get("decided_at") and c["decided_at"] < cutoff:
            eligible = True
        if eligible:
            entry = history_entry("archived", SYSTEM_ACTOR,
                                  internal_notes=f"Auto-archived after {PROPOSAL_ARCHIVE_DAYS}d retention")
            await db.campaigns.update_one({"id": c["id"]},
                                           {"$set": {"is_archived": True,
                                                      "archived_at": now_iso(),
                                                      "archived_by": "system"},
                                            "$push": {"history": entry}})
            archived += 1

    async for s in db.sponsorships.find({"is_archived": {"$ne": True},
                                          "status": {"$in": ["approved", "rejected"]}}):
        if s.get("decided_at") and s["decided_at"] < cutoff:
            entry = history_entry("archived", SYSTEM_ACTOR,
                                  internal_notes=f"Auto-archived after {PROPOSAL_ARCHIVE_DAYS}d retention")
            await db.sponsorships.update_one({"id": s["id"]},
                                              {"$set": {"is_archived": True,
                                                         "archived_at": now_iso(),
                                                         "archived_by": "system"},
                                               "$push": {"history": entry}})
            archived += 1

    if archived:
        logger.info(f"auto-archive swept {archived} proposal(s) after {PROPOSAL_ARCHIVE_DAYS}d retention")


async def _loop() -> None:
    logger.info(f"campaign scheduler online (thresholds={CAMPAIGN_REMINDER_DAYS}, "
                f"archive_days={PROPOSAL_ARCHIVE_DAYS}, "
                f"interval={CHECK_INTERVAL_SECONDS}s)")
    # First run after 30s so startup completes
    await asyncio.sleep(30)
    tick = 0
    while True:
        try:
            await _emit_campaign_reminders()
            # Run auto-archive once per 24 hours (every 24 ticks of 1h)
            if tick % 24 == 0:
                await _auto_archive_proposals()
        except Exception as e:
            logger.error(f"campaign scheduler loop error: {e}")
        tick += 1
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler() -> asyncio.Task:
    return asyncio.create_task(_loop())


# Exposed for manual triggering (e.g. tests / admin endpoint)
async def run_once() -> None:
    await _emit_campaign_reminders()
    await _auto_archive_proposals()
