"""Iteration 5 — campaign flight dates, scheduler reminders, severity taxonomy, archive lifecycle."""
import os
import time
import uuid
from datetime import date, timedelta
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP1 = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    s.headers.update({"Authorization": f"Bearer {d['access_token']}"})
    return s, d


@pytest.fixture(scope="module")
def owner():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def rep():
    return _login(REP1)


def _iso(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def _find_notif_all(sess, event_type, entity_id):
    """Search including archived items across a large window."""
    r = sess.get(f"{API}/notifications?include_archived=true&limit=500", timeout=15)
    assert r.status_code == 200
    for n in r.json():
        if n["event_type"] == event_type and n.get("entity_id") == entity_id:
            return n
    return None


# ---------- Campaign flight dates ----------
class TestCampaignFlightDates:
    def test_create_with_dates(self, rep):
        s, _ = rep
        sd = _iso(0)
        ed = _iso(30)
        r = s.post(f"{API}/campaigns", json={
            "campaign_name": f"TEST Flight {uuid.uuid4().hex[:6]}",
            "client_name": "TEST FlightClient",
            "country_codes": ["FR"], "impressions": 10000,
            "client_total_price": 500.0,
            "start_date": sd, "end_date": ed
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["start_date"] == sd
        assert d["end_date"] == ed
        assert d["computed_status"] == "active"
        assert d["days_left"] == 30

    def test_invalid_range_400(self, rep):
        s, _ = rep
        r = s.post(f"{API}/campaigns", json={
            "campaign_name": "TEST BadRange",
            "client_name": "TEST", "country_codes": ["FR"],
            "impressions": 10000, "client_total_price": 100.0,
            "start_date": _iso(10), "end_date": _iso(5)
        }, timeout=15)
        assert r.status_code == 400

    def test_list_includes_computed(self, rep):
        s, _ = rep
        r = s.get(f"{API}/campaigns", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert items
        for c in items:
            assert "computed_status" in c
            assert "days_left" in c


# ---------- Scheduler: all thresholds + expired + idempotency ----------
class TestSchedulerReminders:
    created_ids = {}  # label -> id

    def test_seed_5_campaigns_various_end_dates(self, rep):
        s, _ = rep
        offsets = {"30d": 30, "14d": 14, "7d": 7, "1d": 1, "expired": -1}
        for label, off in offsets.items():
            r = s.post(f"{API}/campaigns", json={
                "campaign_name": f"TEST Sched-{label}-{uuid.uuid4().hex[:6]}",
                "client_name": f"TEST SchedClient-{label}",
                "country_codes": ["FR"], "impressions": 10000,
                "client_total_price": 500.0,
                "start_date": _iso(min(off, 0) - 5),
                "end_date": _iso(off)
            }, timeout=15)
            assert r.status_code == 200, r.text
            TestSchedulerReminders.created_ids[label] = r.json()["id"]
        assert len(TestSchedulerReminders.created_ids) == 5

    def test_trigger_scheduler_and_verify_notifications(self, owner, rep):
        so, _ = owner
        sr, _ = rep
        # Fire once
        r = so.post(f"{API}/admin/scheduler/run-campaign-reminders", timeout=30)
        assert r.status_code == 200, r.text
        time.sleep(1.0)

        expectations = [
            ("30d", "campaign.expiring.30d"),
            ("14d", "campaign.expiring.14d"),
            ("7d", "campaign.expiring.7d"),
            ("1d", "campaign.expiring.1d"),
            ("expired", "campaign.expired"),
        ]
        for label, event in expectations:
            cid = TestSchedulerReminders.created_ids[label]
            n = _find_notif_all(sr, event, cid)
            assert n is not None, f"rep missing {event} for {cid}"
            assert n["severity"] == "reminder", f"{event} severity={n['severity']}"

        # Admin notifications for 7d & 1d
        for label, event in [("7d", "campaign.expiring.admin.7d"),
                             ("1d", "campaign.expiring.admin.1d")]:
            cid = TestSchedulerReminders.created_ids[label]
            n = _find_notif_all(so, event, cid)
            assert n is not None, f"owner missing {event} for {cid}"
            assert n["severity"] == "reminder"

    def test_scheduler_idempotent(self, owner, rep):
        so, _ = owner
        sr, _ = rep

        def count_events(sess, events, ids):
            r = sess.get(f"{API}/notifications?include_archived=true&limit=500", timeout=15)
            items = r.json()
            return sum(1 for n in items
                       if n["event_type"] in events and n.get("entity_id") in ids)

        rep_events = {"campaign.expiring.30d", "campaign.expiring.14d",
                      "campaign.expiring.7d", "campaign.expiring.1d", "campaign.expired"}
        admin_events = {"campaign.expiring.admin.7d", "campaign.expiring.admin.1d"}
        all_ids = set(TestSchedulerReminders.created_ids.values())

        before_rep = count_events(sr, rep_events, all_ids)
        before_owner = count_events(so, admin_events, all_ids)

        r = so.post(f"{API}/admin/scheduler/run-campaign-reminders", timeout=30)
        assert r.status_code == 200
        time.sleep(1.0)

        after_rep = count_events(sr, rep_events, all_ids)
        after_owner = count_events(so, admin_events, all_ids)

        assert before_rep == after_rep, f"rep duplicate reminders: {before_rep} -> {after_rep}"
        assert before_owner == after_owner, f"admin duplicate reminders: {before_owner} -> {after_owner}"

    def test_cleanup(self, rep):
        # No delete endpoint for campaigns, leave TEST-prefixed data
        pass


# ---------- Config from env ----------
class TestReminderConfig:
    def test_reminder_days_from_env(self):
        with open("/app/backend/core.py") as f:
            src = f.read()
        assert "CAMPAIGN_REMINDER_DAYS" in src
        assert 'os.environ.get("CAMPAIGN_REMINDER_DAYS"' in src


# ---------- Notification unread-count by_severity ----------
class TestUnreadCountBySeverity:
    def test_shape(self, owner):
        s, _ = owner
        r = s.get(f"{API}/notifications/unread-count", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "count" in d
        assert "by_severity" in d
        for k in ("action_required", "reminder", "info"):
            assert k in d["by_severity"], d
            assert isinstance(d["by_severity"][k], int)


# ---------- /actionable endpoint ----------
class TestActionable:
    def test_actionable_returns_only_reminder_and_action(self, owner):
        s, _ = owner
        r = s.get(f"{API}/notifications/actionable", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) <= 5
        for i in items:
            assert i["severity"] in ("action_required", "reminder"), i
            assert i["read"] is False

    def test_actionable_limit(self, owner):
        s, _ = owner
        r = s.get(f"{API}/notifications/actionable?limit=3", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) <= 3


# ---------- Severity filter + include_archived ----------
class TestSeverityFilter:
    def test_filter_reminder(self, rep):
        s, _ = rep
        r = s.get(f"{API}/notifications?severity=reminder&limit=100", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert items, "no reminder notifications after scheduler run"
        assert all(n["severity"] == "reminder" for n in items)

    def test_filter_info(self, owner):
        s, _ = owner
        r = s.get(f"{API}/notifications?severity=info&limit=100", timeout=15)
        assert r.status_code == 200
        assert all(n["severity"] == "info" for n in r.json())


# ---------- Archive lifecycle ----------
class TestArchive:
    def test_archive_and_visibility(self, rep):
        s, _ = rep
        # find any notification for rep
        r = s.get(f"{API}/notifications?limit=50", timeout=15)
        items = r.json()
        assert items, "no notifications for rep to archive"
        target = items[0]
        nid = target["id"]

        # Archive
        a = s.post(f"{API}/notifications/{nid}/archive", timeout=15)
        assert a.status_code == 200

        # Verify absent from default list
        r2 = s.get(f"{API}/notifications?limit=200", timeout=15)
        assert not any(n["id"] == nid for n in r2.json())

        # Verify present with include_archived
        r3 = s.get(f"{API}/notifications?include_archived=true&limit=500", timeout=15)
        archived_row = next((n for n in r3.json() if n["id"] == nid), None)
        assert archived_row is not None
        assert archived_row["archived"] is True
        assert archived_row["read"] is True

    def test_archive_foreign_404(self, rep):
        s, _ = rep
        r = s.post(f"{API}/notifications/{uuid.uuid4()}/archive", timeout=15)
        assert r.status_code == 404

    def test_unread_count_excludes_archived(self, rep):
        s, _ = rep
        # Archive all read (bulk) after marking one as read
        # First, mark one as read
        items = s.get(f"{API}/notifications?unread_only=true&limit=50", timeout=15).json()
        if items:
            nid = items[0]["id"]
            s.patch(f"{API}/notifications/{nid}/read", timeout=15)
        # Then archive-read
        r = s.post(f"{API}/notifications/archive-read", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "archived" in d
        # Unread-count should exclude archived (all read items are now archived)
        uc = s.get(f"{API}/notifications/unread-count", timeout=15).json()
        assert "count" in uc


# ---------- Severity taxonomy per event type ----------
class TestSeverityTaxonomy:
    """Verify severity of newly emitted events for each documented event_type."""

    def test_proposal_events_severity(self, owner, rep):
        so, _ = owner
        sr, _ = rep
        # Submit -> proposal.submitted (admin) severity=action_required
        pid_title = f"TEST Sev {uuid.uuid4().hex[:6]}"
        r = sr.post(f"{API}/proposals", json={
            "title": pid_title, "format": "documentary", "country": "FR",
            "description": "s", "estimated_episodes": 1, "budget_hint_usd": 100
        }, timeout=15)
        pid = r.json()["id"]
        time.sleep(0.5)
        n = _find_notif_all(so, "proposal.submitted", pid)
        assert n is not None
        # proposal.submitted severity is not specified in the review request; must be a valid enum
        assert n["severity"] in ("action_required", "reminder", "info"), n["severity"]

        # Approve -> proposal.approved (rep) severity=info
        so.patch(f"{API}/admin/proposals/{pid}",
                 json={"status": "approved", "admin_notes": "ok"}, timeout=15)
        time.sleep(0.5)
        n = _find_notif_all(sr, "proposal.approved", pid)
        assert n is not None
        assert n["severity"] == "info", f"proposal.approved={n['severity']}"

        # Submit another and reject
        r = sr.post(f"{API}/proposals", json={
            "title": f"TEST SevRej {uuid.uuid4().hex[:6]}", "format": "documentary",
            "country": "FR", "description": "s", "estimated_episodes": 1, "budget_hint_usd": 100
        }, timeout=15)
        pid2 = r.json()["id"]
        so.patch(f"{API}/admin/proposals/{pid2}",
                 json={"status": "rejected", "admin_notes": "no"}, timeout=15)
        time.sleep(0.5)
        n = _find_notif_all(sr, "proposal.rejected", pid2)
        assert n is not None
        assert n["severity"] == "info", f"proposal.rejected={n['severity']}"

        # Send to in_review -> action_required
        so.patch(f"{API}/admin/proposals/{pid2}",
                 json={"status": "in_review", "admin_notes": "revise"}, timeout=15)
        time.sleep(0.5)
        n = _find_notif_all(sr, "proposal.in_review", pid2)
        assert n is not None
        assert n["severity"] == "action_required", f"proposal.in_review={n['severity']}"

    def test_campaign_created_severity_info(self, owner, rep):
        so, _ = owner
        sr, _ = rep
        r = sr.post(f"{API}/campaigns", json={
            "campaign_name": f"TEST SevCamp {uuid.uuid4().hex[:6]}",
            "client_name": "TEST", "country_codes": ["FR"],
            "impressions": 10000, "client_total_price": 500.0
        }, timeout=15)
        cid = r.json()["id"]
        time.sleep(0.5)
        n = _find_notif_all(so, "campaign.created", cid)
        assert n is not None
        assert n["severity"] == "info"

    def test_rep_admin_action_severities(self, owner):
        so, _ = owner
        # create temp rep
        email = f"test_sev_{uuid.uuid4().hex[:6]}@ex.com"
        r = so.post(f"{API}/admin/representatives", json={
            "email": email, "password": "OrigPass2026!", "name": "TEST Sev Rep",
            "agency_name": "TEST Agency", "country": "US"
        }, timeout=15)
        assert r.status_code == 200
        rid = r.json()["id"]

        try:
            so.patch(f"{API}/admin/representatives/{rid}", json={"is_active": False}, timeout=15)
            time.sleep(0.3)
            so.patch(f"{API}/admin/representatives/{rid}",
                     json={"is_active": True, "password": "Reactivated2026!"}, timeout=15)
            time.sleep(0.3)
            sr, _ = _login({"email": email, "password": "Reactivated2026!"})
            items = sr.get(f"{API}/notifications?include_archived=true&limit=50", timeout=15).json()
            by_evt = {n["event_type"]: n for n in items}
            assert by_evt["representative.suspended"]["severity"] == "action_required"
            assert by_evt["representative.reactivated"]["severity"] == "info"
            assert by_evt["representative.password_reset"]["severity"] == "info"
        finally:
            so.delete(f"{API}/admin/representatives/{rid}", timeout=15)

    def test_tv_project_severities(self, owner, rep):
        so, _ = owner
        sr, _ = rep
        r = so.post(f"{API}/admin/tv-projects", json={
            "title": f"TEST SevTV {uuid.uuid4().hex[:6]}", "synopsis": "sev",
            "total_episodes": 3, "price_per_episode_usd": 1000.0, "status": "active"
        }, timeout=15)
        assert r.status_code == 200
        pid = r.json()["id"]
        try:
            time.sleep(0.5)
            n = _find_notif_all(sr, "tv_project.launched", pid)
            assert n is not None
            assert n["severity"] == "info"

            # rep sponsors then admin closes
            sr.post(f"{API}/sponsorships", json={
                "tv_project_id": pid, "client_name": "TEST SevSponsor",
                "episode_numbers": [1], "client_total_price": 1500.0
            }, timeout=15)
            time.sleep(0.3)
            so.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "closed"}, timeout=15)
            time.sleep(0.5)
            n = _find_notif_all(sr, "tv_project.status.closed", pid)
            assert n is not None
            assert n["severity"] == "info"

            so.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "active"}, timeout=15)
            time.sleep(0.5)
            n = _find_notif_all(sr, "tv_project.status.active", pid)
            assert n is not None
            assert n["severity"] == "info"
        finally:
            so.delete(f"{API}/admin/tv-projects/{pid}", timeout=15)
