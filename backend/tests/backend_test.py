"""Independent Media Hub backend tests."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://agency-operations-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP1 = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}
REP2 = {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data and "user" in data
    s.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    return s, data


@pytest.fixture(scope="module")
def admin_session():
    s, d = _login(ADMIN)
    return s, d


@pytest.fixture(scope="module")
def rep_session():
    s, d = _login(REP1)
    return s, d


# ---------- Auth ----------
class TestAuth:
    def test_login_wrong_pw(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "x"}, timeout=15)
        assert r.status_code == 401

    def test_login_admin(self, admin_session):
        s, d = admin_session
        assert d["user"]["role"] == "owner"

    def test_login_rep(self, rep_session):
        s, d = rep_session
        assert d["user"]["role"] == "representative"

    def test_me(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "owner"

    def test_me_no_auth(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ---------- Admin CRUD reps ----------
class TestReps:
    created_id = None

    def test_list_reps(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/admin/representatives", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_rep_forbidden_admin_ep(self, rep_session):
        s, _ = rep_session
        r = s.get(f"{API}/admin/representatives", timeout=15)
        assert r.status_code == 403

    def test_create_rep(self, admin_session):
        s, _ = admin_session
        payload = {"email": "test_newrep@example.com", "password": "TestPass2026!",
                   "name": "TEST Rep", "agency_name": "TEST Agency", "country": "US"}
        r = s.post(f"{API}/admin/representatives", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["email"] == payload["email"]
        assert d["role"] == "representative"
        TestReps.created_id = d["id"]

    def test_suspend_rep(self, admin_session):
        s, _ = admin_session
        assert TestReps.created_id
        r = s.patch(f"{API}/admin/representatives/{TestReps.created_id}",
                    json={"is_active": False}, timeout=15)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_reset_pw(self, admin_session):
        s, _ = admin_session
        r = s.patch(f"{API}/admin/representatives/{TestReps.created_id}",
                    json={"password": "NewPass2026!", "is_active": True}, timeout=15)
        assert r.status_code == 200
        # new pw should work
        r2 = requests.post(f"{API}/auth/login",
                           json={"email": "test_newrep@example.com", "password": "NewPass2026!"}, timeout=15)
        assert r2.status_code == 200

    def test_cleanup(self, admin_session):
        s, _ = admin_session
        if TestReps.created_id:
            r = s.delete(f"{API}/admin/representatives/{TestReps.created_id}", timeout=15)
            assert r.status_code == 200


# ---------- Banner Inventory ----------
class TestInventory:
    def test_list(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/banner-inventory", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 40

    def test_update_price(self, admin_session):
        s, _ = admin_session
        r = s.put(f"{API}/admin/banner-inventory/FR",
                  json={"country_code": "FR", "country_name": "France", "region": "Europe",
                        "price_cpm_usd": 55.5, "min_impressions": 10000}, timeout=15)
        assert r.status_code == 200
        # verify persistence
        r2 = s.get(f"{API}/banner-inventory", timeout=15)
        fr = next(i for i in r2.json() if i["country_code"] == "FR")
        assert fr["price_cpm_usd"] == 55.5
        # revert
        s.put(f"{API}/admin/banner-inventory/FR",
              json={"country_code": "FR", "country_name": "France", "region": "Europe",
                    "price_cpm_usd": 35.0, "min_impressions": 10000}, timeout=15)


# ---------- TV Projects ----------
class TestTV:
    def test_list(self, rep_session):
        s, _ = rep_session
        r = s.get(f"{API}/tv-projects", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 3

    def test_admin_update(self, admin_session):
        s, _ = admin_session
        pid = s.get(f"{API}/tv-projects", timeout=15).json()[0]["id"]
        r = s.patch(f"{API}/admin/tv-projects/{pid}",
                    json={"tagline": "TEST tagline update"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["tagline"] == "TEST tagline update"


# ---------- Campaigns ----------
class TestCampaigns:
    def test_rep_creates_campaign(self, rep_session):
        s, _ = rep_session
        payload = {"campaign_name": "TEST Campaign", "client_name": "TEST Client",
                   "country_codes": ["FR", "DE"], "impressions": 100000,
                   "client_total_price": 10000.0, "notes": ""}
        r = s.post(f"{API}/campaigns", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["internal_cost_usd"] > 0
        assert d["margin_usd"] == round(10000.0 - d["internal_cost_usd"], 2)

    def test_admin_cannot_create_campaign(self, admin_session):
        s, _ = admin_session
        r = s.post(f"{API}/campaigns",
                   json={"campaign_name": "X", "client_name": "X", "country_codes": ["FR"],
                         "impressions": 10000, "client_total_price": 100.0}, timeout=15)
        assert r.status_code == 403


# ---------- Sponsorships ----------
class TestSponsorships:
    def test_flow(self, rep_session):
        s, _ = rep_session
        tv = s.get(f"{API}/tv-projects", timeout=15).json()
        # pick project with any un-sponsored episode
        project = tv[0]
        taken = set(project.get("sponsored_episodes", []))
        ep = next(e for e in range(1, project["total_episodes"] + 1) if e not in taken)
        payload = {"tv_project_id": project["id"], "client_name": "TEST Sponsor",
                   "episode_numbers": [ep], "client_total_price": 5000.0}
        r = s.post(f"{API}/sponsorships", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        # conflict
        r2 = s.post(f"{API}/sponsorships", json=payload, timeout=15)
        assert r2.status_code == 409


# ---------- Proposals ----------
class TestProposals:
    pid = None

    def test_rep_submits(self, rep_session):
        s, _ = rep_session
        r = s.post(f"{API}/proposals",
                   json={"title": "TEST Proposal", "format": "documentary", "country": "FR",
                         "description": "test desc", "estimated_episodes": 6,
                         "budget_hint_usd": 50000}, timeout=15)
        assert r.status_code == 200
        TestProposals.pid = r.json()["id"]
        assert r.json()["status"] == "in_review"

    def test_admin_decide(self, admin_session):
        s, _ = admin_session
        r = s.patch(f"{API}/admin/proposals/{TestProposals.pid}",
                    json={"status": "approved", "admin_notes": "Looks great"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "approved"
        assert r.json()["admin_notes"] == "Looks great"


# ---------- Reports ----------
class TestReports:
    def test_admin_overview(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/reports/overview", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "owner"
        assert "total_reps_active" in d and d["total_reps_active"] >= 2
        assert "proposals_pending" in d

    def test_rep_overview_scoped(self, rep_session):
        s, _ = rep_session
        r = s.get(f"{API}/reports/overview", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "representative"
        assert d["total_reps_active"] == 0  # not exposed to rep


# ---------- Countries ----------
class TestCountries:
    def test_list(self, rep_session):
        s, _ = rep_session
        r = s.get(f"{API}/countries", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 40


# ---------- P1/P2: Owner admins management ----------
class TestOwnerAdmins:
    created_admin_id = None
    admin_token = None

    def test_list_admins(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/owner/admins", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert any(u["role"] == "owner" for u in data)

    def test_rep_forbidden(self, rep_session):
        s, _ = rep_session
        r = s.get(f"{API}/owner/admins", timeout=15)
        assert r.status_code == 403

    def test_create_admin(self, admin_session):
        s, _ = admin_session
        payload = {"email": "test_admin2@example.com", "password": "AdminPass2026!", "name": "TEST Admin2"}
        r = s.post(f"{API}/owner/admins", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["role"] == "admin"
        assert d["email"] == payload["email"]
        TestOwnerAdmins.created_admin_id = d["id"]
        # login as this admin
        r2 = requests.post(f"{API}/auth/login", json={"email": payload["email"], "password": payload["password"]}, timeout=15)
        assert r2.status_code == 200
        TestOwnerAdmins.admin_token = r2.json()["access_token"]

    def test_admin_cannot_create_admin(self):
        assert TestOwnerAdmins.admin_token
        headers = {"Authorization": f"Bearer {TestOwnerAdmins.admin_token}"}
        r = requests.post(f"{API}/owner/admins",
                          json={"email": "test_x@example.com", "password": "x", "name": "x"},
                          headers=headers, timeout=15)
        assert r.status_code == 403

    def test_admin_cannot_delete(self):
        assert TestOwnerAdmins.admin_token and TestOwnerAdmins.created_admin_id
        headers = {"Authorization": f"Bearer {TestOwnerAdmins.admin_token}"}
        r = requests.delete(f"{API}/owner/admins/{TestOwnerAdmins.created_admin_id}", headers=headers, timeout=15)
        assert r.status_code == 403

    def test_cannot_delete_owner(self, admin_session):
        s, d = admin_session
        r = s.delete(f"{API}/owner/admins/{d['user']['id']}", timeout=15)
        assert r.status_code == 400

    def test_delete_admin(self, admin_session):
        s, _ = admin_session
        r = s.delete(f"{API}/owner/admins/{TestOwnerAdmins.created_admin_id}", timeout=15)
        assert r.status_code == 200


# ---------- P1/P2: TV Project status controls ----------
class TestTVStatus:
    project_id = None
    original_status = None

    def test_set_draft(self, admin_session):
        s, _ = admin_session
        pid = s.get(f"{API}/tv-projects?status=active", timeout=15).json()[0]["id"]
        TestTVStatus.project_id = pid
        TestTVStatus.original_status = "active"
        r = s.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "draft"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_draft_filter(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/tv-projects?status=draft", timeout=15)
        assert r.status_code == 200
        assert all(p["status"] == "draft" for p in r.json())
        assert any(p["id"] == TestTVStatus.project_id for p in r.json())

    def test_rep_hides_non_active(self, rep_session):
        s, _ = rep_session
        r = s.get(f"{API}/tv-projects", timeout=15)
        assert r.status_code == 200
        assert all(p.get("status", "active") == "active" for p in r.json())
        assert not any(p["id"] == TestTVStatus.project_id for p in r.json())

    def test_set_closed(self, admin_session):
        s, _ = admin_session
        r = s.patch(f"{API}/admin/tv-projects/{TestTVStatus.project_id}/status",
                    json={"status": "closed"}, timeout=15)
        assert r.status_code == 200

    def test_invalid_status(self, admin_session):
        s, _ = admin_session
        r = s.patch(f"{API}/admin/tv-projects/{TestTVStatus.project_id}/status",
                    json={"status": "bogus"}, timeout=15)
        assert r.status_code == 400

    def test_restore_active(self, admin_session):
        s, _ = admin_session
        r = s.patch(f"{API}/admin/tv-projects/{TestTVStatus.project_id}/status",
                    json={"status": "active"}, timeout=15)
        assert r.status_code == 200


# ---------- P1/P2: Per-country impressions override ----------
class TestPerCountry:
    def test_campaign_with_overrides(self, rep_session):
        s, _ = rep_session
        payload = {
            "campaign_name": "TEST PerCountry",
            "client_name": "TEST Client PC",
            "country_codes": ["FR", "DE"],
            "impressions": 100000,
            "client_total_price": 12345.0,
            "per_country_impressions": {"FR": 150000, "DE": 50000},
        }
        r = s.post(f"{API}/campaigns", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        # verify via list
        listing = s.get(f"{API}/campaigns", timeout=15).json()
        me = next(c for c in listing if c["id"] == d["id"])
        pc_map = {p["country_code"]: p["impressions"] for p in me["per_country"]}
        assert pc_map.get("FR") == 150000
        assert pc_map.get("DE") == 50000


# ---------- P1/P2: Audit Log ----------
class TestAuditLog:
    def test_owner_can_view(self, admin_session, rep_session):
        s, _ = admin_session
        sr, _ = rep_session
        # Seed some events in this test to avoid xdist ordering flakiness
        sr.post(f"{API}/campaigns", json={
            "campaign_name": "TEST Audit", "client_name": "TEST",
            "country_codes": ["FR"], "impressions": 10000, "client_total_price": 500.0
        }, timeout=15)
        pid = s.get(f"{API}/tv-projects?status=active", timeout=15).json()[0]["id"]
        s.patch(f"{API}/admin/tv-projects/{pid}/status", json={"status": "active"}, timeout=15)
        s.put(f"{API}/admin/banner-inventory/FR", json={
            "country_code": "FR", "country_name": "France", "region": "Europe",
            "price_cpm_usd": 35.0, "min_impressions": 10000
        }, timeout=15)

        r = s.get(f"{API}/admin/audit-log", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) > 0
        actions = {i["action"] for i in items}
        assert any(a.startswith("campaign.create") for a in actions), f"no campaign.create in {actions}"
        assert any(a.startswith("tv_project.status.") for a in actions), f"no tv_project.status in {actions}"
        assert "inventory.update" in actions
        # entry structure
        e = items[0]
        assert "action" in e and "entity_type" in e and "actor_role" in e and "created_at" in e

    def test_rep_forbidden(self, rep_session):
        s, _ = rep_session
        r = s.get(f"{API}/admin/audit-log", timeout=15)
        assert r.status_code == 403

    def test_filter_entity_type(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/admin/audit-log?entity_type=campaign", timeout=15)
        assert r.status_code == 200
        assert all(i["entity_type"] == "campaign" for i in r.json())

    def test_filter_actor_role(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/admin/audit-log?actor_role=representative", timeout=15)
        assert r.status_code == 200
        assert all(i["actor_role"] == "representative" for i in r.json())


# ---------- P1: Resend password reset (RESEND_API_KEY empty -> falls back to log) ----------
class TestPasswordReset:
    def test_forgot_and_reset(self):
        # Create a temp rep via owner
        s_owner, _ = _login(ADMIN)
        payload = {"email": "test_resetuser@example.com", "password": "OrigPass2026!",
                   "name": "TEST Reset", "agency_name": "TEST Agency", "country": "US"}
        cr = s_owner.post(f"{API}/admin/representatives", json=payload, timeout=15)
        assert cr.status_code == 200
        rid = cr.json()["id"]

        try:
            r = requests.post(f"{API}/auth/forgot-password", json={"email": payload["email"]}, timeout=15)
            assert r.status_code == 200
            assert r.json().get("ok") is True

            # grab token from log
            import subprocess, re
            out = subprocess.run(
                ["bash", "-lc",
                 "grep -h 'PASSWORD RESET\\|reset link' /var/log/supervisor/backend.*.log | tail -50"],
                capture_output=True, text=True, timeout=10
            ).stdout
            # token is in URL: /reset-password?token=<hex>
            m = re.search(r"token=([A-Za-z0-9_\-]+)", out)
            assert m, f"reset token not found in backend logs. tail=\n{out[-1000:]}"
            token = m.group(1)

            r2 = requests.post(f"{API}/auth/reset-password",
                               json={"token": token, "new_password": "NewReset2026!"}, timeout=15)
            assert r2.status_code == 200, r2.text

            # login with new password
            r3 = requests.post(f"{API}/auth/login",
                               json={"email": payload["email"], "password": "NewReset2026!"}, timeout=15)
            assert r3.status_code == 200
        finally:
            s_owner.delete(f"{API}/admin/representatives/{rid}", timeout=15)


# ---------- Non-existent forgot-password (still 200 to prevent enumeration) ----------
class TestForgotUnknown:
    def test_unknown_email(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": "nobody@example.com"}, timeout=15)
        assert r.status_code == 200
