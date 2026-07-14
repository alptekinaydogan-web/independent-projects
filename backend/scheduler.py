"""Background scheduler: campaign expiration reminders.

Runs an hourly loop on the FastAPI event loop. For every campaign with an
end_date, checks whether `days_left` equals one of the configured reminder
thresholds (default 30/14/7/1) and, if we have not already emitted that
specific reminder for the campaign, notifies the owning representative and
all administrators. Also emits a `campaign.expired` reminder the day after
the campaign ends (once).

Configuration:
    CAMPAIGN_REMINDER_DAYS  — comma-separated days (default "30,14,7,1")
"""
import asyncio
from datetime import datetime, timezone
from core import db, logger, CAMPAIGN_REMINDER_DAYS
from notifications import notify, notify_all_admins

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


async def _loop() -> None:
    logger.info(f"campaign scheduler online (thresholds={CAMPAIGN_REMINDER_DAYS}, "
                f"interval={CHECK_INTERVAL_SECONDS}s)")
    # First run after 30s so startup completes
    await asyncio.sleep(30)
    while True:
        try:
            await _emit_campaign_reminders()
        except Exception as e:
            logger.error(f"campaign scheduler loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler() -> asyncio.Task:
    return asyncio.create_task(_loop())


# Exposed for manual triggering (e.g. tests / admin endpoint)
async def run_once() -> None:
    await _emit_campaign_reminders()
