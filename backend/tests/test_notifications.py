"""Notification center end-to-end tests (iteration 4)."""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"

ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP1 = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}
REP2 = {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!"}


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
def rep1():
    return _login(REP1)


@pytest.fixture(scope="module")
def rep2():
    return _login(REP2)


def _mark_all(sess):
    sess.post(f"{API}/notifications/mark-all-read", json={}, timeout=15)


def _find_notif(sess, event_type, entity_id=None, limit=50):
    r = sess.get(f"{API}/notifications?limit={limit}", timeout=15)
    assert r.status_code == 200
    for n in r.json():
        if n["event_type"] == event_type and (entity_id is None or n.get("entity_id") == entity_id):
            return n
    return None


# ---------- Basic endpoints ----------
class TestNotifBasicEndpoints:
    def test_list_requires_auth(self):
        r = requests.get(f"{API}/notifications", timeout=15)
        assert r.status_code == 401

    def test_unread_count(self, owner):
        s, _ = owner
        r = s.get(f"{API}/notifications/unread-count", timeout=15)
        assert r.status_code == 200
        assert "count" in r.json()
        assert isinstance(r.json()["count"], int)

    def test_list_sorted_desc(self, owner):
        s, _ = owner
        r = s.get(f"{API}/notifications?limit=20", timeout=15)
        assert r.status_code == 200
        items = r.json()
        if len(items) >= 2:
            assert items[0]["created_at"] >= items[1]["created_at"]

    def test_mark_read_404_when_not_owned(self, owner):
        s, _ = owner
        r = s.patch(f"{API}/notifications/{uuid.uuid4()}/read", timeout=15)
        assert r.status_code == 404

    def test_unread_only_filter(self, owner):
        s, _ = owner
        # Fire a fresh proposal to guarantee at least one unread for owner
        srep, _ = _login(REP1)
        srep.post(f"{API}/proposals", json={
            "title": f"TEST notif filter {uuid.uuid4().hex[:6]}",
            "format": "documentary", "country": "FR",
            "description": "x", "estimated_episodes": 1, "budget_hint_usd": 100
        }, timeout=15)
        time.sleep(0.5)
        r = s.get(f"{API}/notifications?unread_only=true&limit=50", timeout=15)
        assert r.status_code == 200
        assert all(n["read"] is False for n in r.json())


# ---------- Proposal notifications ----------
class TestProposalNotifications:
    def test_submit_notifies_admin(self, owner, rep1):
        so, _ = owner
        sr, _ = rep1
        _mark_all(so)
        title = f"TEST notif proposal {uuid.uuid4().hex[:6]}"
        r = sr.post(f"{API}/proposals", json={
            "title": title, "format": "documentary", "country": "DE",
            "description": "notify test", "estimated_episodes": 3, "budget_hint_usd": 5000
        }, timeout=15)
        assert r.status_code == 200
        pid = r.json()["id"]
        time.sleep(0.6)
        n = _find_notif(so, "proposal.submitted", entity_id=pid)
        assert n is not None, "admin did not receive proposal.submitted"
        assert title in n["title"]
        # cleanup: leave proposal in DB (marked TEST)

    def test_decide_notifies_rep_and_dedup(self, owner, rep1):
        so, _ = owner
        sr, rep_data = rep1
        # Submit
        title = f"TEST notif decide {uuid.uuid4().hex[:6]}"
        r = sr.post(f"{API}/proposals", json={
            "title": title, "format": "documentary", "country": "GB",
            "description": "d", "estimated_episodes": 4, "budget_hint_usd": 8000
        }, timeout=15)
        pid = r.json()["id"]
        _mark_all(sr)
        # Approve with note
        note = "Notes-XYZ-777"
        d = so.patch(f"{API}/admin/proposals/{pid}",
                     json={"status": "approved", "admin_notes": note}, timeout=15)
        assert d.status_code == 200
        time.sleep(0.6)
        n = _find_notif(sr, "proposal.approved", entity_id=pid)
        assert n, "rep did not receive proposal.approved"
        assert note in n["message"]

        # Same-status update must NOT emit another notification
        _mark_all(sr)
        d2 = so.patch(f"{API}/admin/proposals/{pid}",
                      json={"status": "approved", "admin_notes": note}, timeout=15)
        assert d2.status_code == 200
        time.sleep(0.6)
        n2 = _find_notif(sr, "proposal.approved", entity_id=pid)
        # After mark-all-read, if a new notif was emitted, it would appear unread now
        cnt = sr.get(f"{API}/notifications/unread-count", timeout=15).json()["count"]
        assert cnt == 0, f"duplicate notification emitted on same-status update (unread={cnt})"


# ---------- Campaign notifications ----------
class TestCampaignNotifications:
    def test_create_campaign_notifies_admin(self, owner, rep1):
        so, _ = owner
        sr, _ = rep1
        _mark_all(so)
        r = sr.post(f"{API}/campaigns", json={
            "campaign_name": f"TEST NotifCamp {uuid.uuid4().hex[:6]}",
            "client_name": "TEST NotifClient",
            "country_codes": ["FR"], "impressions": 20000,
            "client_total_price": 1500.0
        }, timeout=15)
        assert r.status_code == 200
        cid = r.json()["id"]
        time.sleep(0.6)
        n = _find_notif(so, "campaign.created", entity_id=cid)
        assert n is not None
        assert "TEST NotifClient" in n["message"]
        assert "1,500" in n["message"] or "1500" in n["message"]


# ---------- Sponsorship notifications + non-active guard ----------
class TestSponsorshipNotifications:
    def test_create_sponsorship_notifies_admin(self, owner, rep1):
        so, _ = owner
        sr, _ = rep1
        # Pick an active project with a free ep
        projs = sr.get(f"{API}/tv-projects", timeout=15).json()
        assert projs
        proj = projs[0]
        taken = set(proj.get("sponsored_episodes", []))
        ep = next(e for e in range(1, proj["total_episodes"] + 1) if e not in taken)
        _mark_all(so)
        r = sr.post(f"{API}/sponsorships", json={
            "tv_project_id": proj["id"], "client_name": "TEST Sponsor Notif",
            "episode_numbers": [ep], "client_total_price": 3000.0
        }, timeout=15)
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        time.sleep(0.6)
        n = _find_notif(so, "sponsorship.created", entity_id=sid)
        assert n is not None

    def test_sponsorship_blocked_on_non_active(self, owner, rep1):
        so, _ = owner
        sr, _ = rep1
        # find an active project, flip to draft, attempt sponsor
        act = so.get(f"{API}/tv-projects?status=active", timeout=15).json()
        assert act
        pid = act[0]["id"]
        so.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "draft"}, timeout=15)
        try:
            r = sr.post(f"{API}/sponsorships", json={
                "tv_project_id": pid, "client_name": "TEST BadSponsor",
                "episode_numbers": [1], "client_total_price": 100.0
            }, timeout=15)
            assert r.status_code == 400, r.text
        finally:
            so.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "active"}, timeout=15)


# ---------- TV project notifications ----------
class TestTVProjectNotifications:
    created_id = None

    def test_create_active_notifies_reps(self, owner, rep1):
        so, _ = owner
        sr, _ = rep1
        _mark_all(sr)
        title = f"TEST NotifTV {uuid.uuid4().hex[:6]}"
        r = so.post(f"{API}/admin/tv-projects", json={
            "title": title, "synopsis": "notif test",
            "total_episodes": 6, "price_per_episode_usd": 5000.0, "status": "active"
        }, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        TestTVProjectNotifications.created_id = pid
        time.sleep(0.6)
        n = _find_notif(sr, "tv_project.launched", entity_id=pid)
        assert n is not None

    def test_status_toggle_notifications(self, owner, rep1):
        so, _ = owner
        sr, rep_data = rep1
        pid = TestTVProjectNotifications.created_id
        assert pid
        # rep sponsors a single episode so they qualify for closed notification
        _mark_all(sr)
        rs = sr.post(f"{API}/sponsorships", json={
            "tv_project_id": pid, "client_name": "TEST Sponsor Close",
            "episode_numbers": [1], "client_total_price": 6000.0
        }, timeout=15)
        assert rs.status_code == 200

        # active -> closed should notify the sponsoring rep
        _mark_all(sr)
        so.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "closed"}, timeout=15)
        time.sleep(0.6)
        n = _find_notif(sr, "tv_project.status.closed", entity_id=pid)
        assert n is not None, "rep didn't get tv_project.status.closed"

        # closed -> closed no-op
        _mark_all(sr)
        so.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "closed"}, timeout=15)
        time.sleep(0.6)
        assert sr.get(f"{API}/notifications/unread-count", timeout=15).json()["count"] == 0

        # closed -> active notifies all reps
        _mark_all(sr)
        so.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "active"}, timeout=15)
        time.sleep(0.6)
        n = _find_notif(sr, "tv_project.status.active", entity_id=pid)
        assert n is not None

    def test_cleanup(self, owner):
        so, _ = owner
        if TestTVProjectNotifications.created_id:
            so.delete(f"{API}/admin/tv-projects/{TestTVProjectNotifications.created_id}", timeout=15)


# ---------- Rep admin actions ----------
class TestRepAdminActionNotifications:
    rid = None

    def test_setup_temp_rep(self, owner):
        so, _ = owner
        r = so.post(f"{API}/admin/representatives", json={
            "email": f"test_notif_{uuid.uuid4().hex[:6]}@ex.com",
            "password": "OrigPass2026!", "name": "TEST Notif Rep",
            "agency_name": "TEST Agency", "country": "US"
        }, timeout=15)
        assert r.status_code == 200
        TestRepAdminActionNotifications.rid = r.json()["id"]
        TestRepAdminActionNotifications.email = r.json()["email"]

    def test_suspend_and_reactivate_notify(self, owner):
        so, _ = owner
        rid = TestRepAdminActionNotifications.rid
        # suspend
        so.patch(f"{API}/admin/representatives/{rid}", json={"is_active": False}, timeout=15)
        time.sleep(0.4)
        # login as rep - can't (suspended). Need to check as-if we're that rep — but they can't log in.
        # Instead, reactivate first, log in, look back at both notifications.
        so.patch(f"{API}/admin/representatives/{rid}",
                 json={"is_active": True, "password": "Reactivated2026!"}, timeout=15)
        time.sleep(0.4)
        sr, _ = _login({"email": TestRepAdminActionNotifications.email, "password": "Reactivated2026!"})
        items = sr.get(f"{API}/notifications?limit=20", timeout=15).json()
        events = [n["event_type"] for n in items]
        assert "representative.suspended" in events
        assert "representative.reactivated" in events
        assert "representative.password_reset" in events

    def test_no_notify_on_noop(self, owner):
        so, _ = owner
        rid = TestRepAdminActionNotifications.rid
        # Simply change name — no suspension/password fields
        sr, _ = _login({"email": TestRepAdminActionNotifications.email, "password": "Reactivated2026!"})
        _mark_all(sr)
        so.patch(f"{API}/admin/representatives/{rid}", json={"name": "TEST Notif Rep Updated"}, timeout=15)
        time.sleep(0.4)
        cnt = sr.get(f"{API}/notifications/unread-count", timeout=15).json()["count"]
        assert cnt == 0, f"noop update emitted a notification (unread={cnt})"

    def test_cleanup(self, owner):
        so, _ = owner
        if TestRepAdminActionNotifications.rid:
            so.delete(f"{API}/admin/representatives/{TestRepAdminActionNotifications.rid}", timeout=15)


# ---------- Mark-all-read ----------
class TestMarkAll:
    def test_mark_all(self, rep1):
        s, _ = rep1
        # ensure at least one unread
        r = s.post(f"{API}/proposals", json={
            "title": f"TEST markall {uuid.uuid4().hex[:6]}", "format": "documentary",
            "country": "FR", "description": "x", "estimated_episodes": 1, "budget_hint_usd": 100
        }, timeout=15)
        assert r.status_code == 200
        time.sleep(0.3)
        # rep doesn't get their own proposal notif; use existing notifications from previous tests
        m = s.post(f"{API}/notifications/mark-all-read", json={}, timeout=15)
        assert m.status_code == 200
        cnt = s.get(f"{API}/notifications/unread-count", timeout=15).json()["count"]
        assert cnt == 0
