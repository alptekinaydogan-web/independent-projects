"""Iteration 13 — Demo seed endpoint, role gating, rep privacy, notifications fan-out."""
import os
import requests
import pytest
from pathlib import Path

def _load_frontend_env():
    env = Path("/app/frontend/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("REACT_APP_BACKEND_URL", "")

BASE = _load_frontend_env().rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL missing"
API = BASE + "/api"

OWNER = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}
LEGACY = {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    return s, r


@pytest.fixture(scope="module")
def owner_sess():
    s, r = _login(OWNER)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def rep_sess():
    s, r = _login(REP)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module", autouse=True)
def seeded(owner_sess):
    """Seed once at start of module for a clean baseline."""
    r = owner_sess.post(f"{API}/admin/demo/seed", timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- Seed endpoint contract ----------
class TestSeedEndpoint:
    def test_owner_can_seed_and_summary_shape(self, owner_sess):
        r = owner_sess.post(f"{API}/admin/demo/seed", timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "wiped" in data and "created" in data
        c = data["created"]
        assert c["banner_proposals"] >= 15, c
        assert c["sponsorship_proposals"] >= 8, c
        assert c["notifications"] >= 10, c
        assert c["audit_entries"] > 40, c
        assert data["representative"] == "victor.laurent@parismedia.fr"
        assert data["tv_projects_available"] >= 3

    def test_rep_cannot_seed(self, rep_sess):
        r = rep_sess.post(f"{API}/admin/demo/seed", timeout=30)
        assert r.status_code == 403, r.status_code

    def test_unauth_cannot_seed(self):
        r = requests.post(f"{API}/admin/demo/seed", timeout=15)
        assert r.status_code in (401, 403), r.status_code

    def test_idempotent_second_run(self, owner_sess):
        r1 = owner_sess.post(f"{API}/admin/demo/seed", timeout=60).json()
        r2 = owner_sess.post(f"{API}/admin/demo/seed", timeout=60).json()
        # Wiped counts on second run should ~= what first run created
        assert r2["wiped"]["campaigns"] == r1["created"]["banner_proposals"]
        assert r2["wiped"]["sponsorships"] == r1["created"]["sponsorship_proposals"]
        assert r2["created"]["banner_proposals"] == r1["created"]["banner_proposals"]


# ---------- Status coverage ----------
EXPECTED_STATUSES = {"pending_review", "revised", "revision_requested", "approved", "rejected", "archived"}


class TestStatusCoverage:
    def test_banner_all_six_statuses(self, owner_sess):
        r = owner_sess.get(f"{API}/campaigns?include_archived=true", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 15
        statuses = {}
        for it in items:
            st = "archived" if it.get("is_archived") else it.get("status")
            statuses[st] = statuses.get(st, 0) + 1
        for s in EXPECTED_STATUSES:
            assert statuses.get(s, 0) >= 1, f"missing status {s}: {statuses}"

    def test_sponsorship_all_six_statuses(self, owner_sess):
        r = owner_sess.get(f"{API}/sponsorships?include_archived=true", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 8
        statuses = {}
        for it in items:
            st = "archived" if it.get("is_archived") else it.get("status")
            statuses[st] = statuses.get(st, 0) + 1
        for s in EXPECTED_STATUSES:
            assert statuses.get(s, 0) >= 1, f"missing status {s}: {statuses}"


# ---------- Reports ----------
class TestReports:
    def test_reports_overview(self, owner_sess):
        r = owner_sess.get(f"{API}/reports/overview", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["banner_proposals"]["total"] > 0
        assert d["tv_proposals"]["total"] > 0
        assert 3 <= len(d["monthly_series"]) <= 6, len(d["monthly_series"])
        assert len(d["top_networks"]) > 0
        assert d["all_pending_review"] > 0


# ---------- Notifications ----------
class TestNotifications:
    def test_admin_notifications(self, owner_sess):
        r = owner_sess.get(f"{API}/notifications", timeout=20)
        assert r.status_code == 200
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        assert len(items) > 0
        assert any(n.get("severity") == "action_required" and not n.get("read") for n in items)

    def test_rep_notifications(self, rep_sess):
        r = rep_sess.get(f"{API}/notifications", timeout=20)
        assert r.status_code == 200
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        assert len(items) > 0
        assert any(n.get("severity") == "action_required" and not n.get("read") for n in items)


# ---------- Audit log ----------
class TestAuditLog:
    def test_audit_size_and_banner_lifecycle(self, owner_sess):
        r = owner_sess.get(f"{API}/admin/audit-log?limit=500", timeout=20)
        assert r.status_code == 200
        items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        assert len(items) > 40, len(items)
        banner_actions = {i.get("action") for i in items if str(i.get("action", "")).startswith("proposal.banner.")}
        # Must cover multiple lifecycle statuses
        needed = {"proposal.banner.submitted", "proposal.banner.approved"}
        assert needed.issubset(banner_actions), banner_actions
        # At least one of revised/revision_requested/rejected also present
        assert banner_actions & {"proposal.banner.revised", "proposal.banner.revision_requested", "proposal.banner.rejected"}


# ---------- Rep privacy (internal_notes stripped) ----------
def _has_internal_notes_leak(obj):
    """Return True if any 'internal_notes' key contains non-empty content."""
    if isinstance(obj, dict):
        v = obj.get("internal_notes")
        if isinstance(v, str) and v.strip():
            return True
        for val in obj.values():
            if _has_internal_notes_leak(val):
                return True
    elif isinstance(obj, list):
        for x in obj:
            if _has_internal_notes_leak(x):
                return True
    return False


class TestRepPrivacy:
    def test_rep_campaigns_no_internal_notes(self, rep_sess):
        r = rep_sess.get(f"{API}/campaigns?include_archived=true", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert len(items) > 0
        assert not _has_internal_notes_leak(items), "internal_notes leaked to rep in campaigns"

    def test_rep_sponsorships_no_internal_notes(self, rep_sess):
        r = rep_sess.get(f"{API}/sponsorships?include_archived=true", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert len(items) > 0
        assert not _has_internal_notes_leak(items), "internal_notes leaked to rep in sponsorships"


# ---------- Legacy inactive rep ----------
class TestLegacyRepInactive:
    def test_amelia_inactive_via_admin_list(self, owner_sess):
        r = owner_sess.get(f"{API}/admin/representatives", timeout=20)
        assert r.status_code == 200
        reps = r.json()
        amelia = next((u for u in reps if u.get("email") == LEGACY["email"]), None)
        assert amelia is not None, "amelia not present in reps list"
        assert amelia.get("is_active") is False, amelia

    def test_amelia_login_blocked(self):
        s, r = _login(LEGACY)
        # inactive users are rejected with 401 per auth.py
        assert r.status_code == 401, r.status_code
