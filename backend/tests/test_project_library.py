"""Backend tests for the Independent Projects platform after the
banner-marketplace cleanup pivot. Verifies:
  - Categories API + seeding
  - Project Library endpoints and Apply-to-Produce flow
  - Applications decision workflow
  - Partner submissions (proposals)
  - Reports overview shape (no banner fields)
  - Representatives stats shape (no banner fields)
  - System health counters (no campaigns/sponsorships)
  - Legacy endpoints are 404
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

OWNER_EMAIL = "admin@independentmedia.hub"
OWNER_PASSWORD = "Admin2026!"
REP_EMAIL = "victor.laurent@parismedia.fr"
REP_PASSWORD = "Rep2026!"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def owner_headers():
    tok = _login(OWNER_EMAIL, OWNER_PASSWORD)
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def rep_headers():
    tok = _login(REP_EMAIL, REP_PASSWORD)
    return {"Authorization": f"Bearer {tok}"}


# ---------------- Categories ----------------
class TestCategories:
    def test_list_categories(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/categories", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        cats = r.json()
        assert isinstance(cats, list)
        slugs = [c["slug"] for c in cats]
        assert "tv_formats" in slugs
        tv = next(c for c in cats if c["slug"] == "tv_formats")
        assert tv.get("is_active") is True

    def test_get_category_by_slug(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/categories/tv_formats", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["slug"] == "tv_formats"


# ---------------- Project Library ----------------
class TestProjectLibrary:
    def test_list_projects_admin_shape(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/tv-projects", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) > 0
        for p in items:
            assert "id" in p and "category_slug" in p
            assert "pending_applications_count" in p
            assert "approved_applications_count" in p
            assert "_id" not in p

    def test_list_projects_rep_only_active(self, rep_headers):
        r = requests.get(f"{BASE_URL}/api/tv-projects", headers=rep_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert all(p["status"] == "active" for p in items)

    def test_get_project_detail(self, rep_headers):
        r = requests.get(f"{BASE_URL}/api/tv-projects", headers=rep_headers, timeout=15)
        pid = r.json()[0]["id"]
        r2 = requests.get(f"{BASE_URL}/api/tv-projects/{pid}", headers=rep_headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["id"] == pid


# ---------------- Apply-to-Produce ----------------
class TestApplyToProduce:
    def test_apply_and_duplicate_and_decision(self, owner_headers, rep_headers):
        # Fresh project for a clean apply flow
        create_body = {
            "title": f"TEST_APPLY_{uuid.uuid4().hex[:6]}",
            "logline": "A test format.",
            "synopsis": "For automated testing.",
            "genre": "Reality",
            "total_episodes": 10,
            "episode_duration_minutes": 30,
            "target_audience": "Adults 25-54",
            "status": "active",
            "category_slug": "tv_formats",
        }
        cr = requests.post(f"{BASE_URL}/api/admin/tv-projects", json=create_body,
                           headers=owner_headers, timeout=15)
        assert cr.status_code == 200, cr.text
        pid = cr.json()["id"]

        # Apply as rep
        ar = requests.post(f"{BASE_URL}/api/tv-projects/{pid}/apply",
                           json={"tv_project_id": pid,
                                 "message": "Would love to produce in FR",
                                 "target_launch_date": "2026-06-01"},
                           headers=rep_headers, timeout=15)
        assert ar.status_code == 200, ar.text
        app = ar.json()
        assert app["status"] == "submitted"
        app_id = app["id"]

        # Duplicate -> 409
        dup = requests.post(f"{BASE_URL}/api/tv-projects/{pid}/apply",
                            json={"tv_project_id": pid, "message": "again"},
                            headers=rep_headers, timeout=15)
        assert dup.status_code == 409

        # Rep detail should include my_application
        det = requests.get(f"{BASE_URL}/api/tv-projects/{pid}", headers=rep_headers, timeout=15).json()
        assert det.get("my_application", {}).get("id") == app_id

        # My productions lists it
        mine = requests.get(f"{BASE_URL}/api/my-productions", headers=rep_headers, timeout=15)
        assert mine.status_code == 200
        assert any(a["id"] == app_id for a in mine.json())

        # Admin /productions lists it
        all_apps = requests.get(f"{BASE_URL}/api/productions", headers=owner_headers, timeout=15)
        assert all_apps.status_code == 200
        assert any(a["id"] == app_id for a in all_apps.json())

        # Decide -> approved
        dec = requests.patch(f"{BASE_URL}/api/productions/{app_id}/decision",
                             json={"decision": "approved",
                                   "representative_feedback": "Approved for FR"},
                             headers=owner_headers, timeout=15)
        assert dec.status_code == 200, dec.text
        assert dec.json()["status"] == "approved"

        # Invalid decision
        bad = requests.patch(f"{BASE_URL}/api/productions/{app_id}/decision",
                             json={"decision": "bogus"},
                             headers=owner_headers, timeout=15)
        assert bad.status_code == 400

        # Cleanup: delete project (cascades productions)
        requests.delete(f"{BASE_URL}/api/admin/tv-projects/{pid}", headers=owner_headers, timeout=15)


# ---------------- Partner submissions (proposals) ----------------
class TestPartnerSubmissions:
    def test_create_and_decide(self, owner_headers, rep_headers):
        body = {
            "title": f"TEST_PARTNER_{uuid.uuid4().hex[:6]}",
            "format": "Documentary",
            "country": "France",
            "description": "Testing partner submissions.",
            "estimated_episodes": 6,
            "budget_hint_usd": 50000,
        }
        r = requests.post(f"{BASE_URL}/api/proposals", json=body,
                          headers=rep_headers, timeout=15)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]

        dec = requests.patch(f"{BASE_URL}/api/admin/proposals/{pid}",
                             json={"status": "approved", "admin_notes": "great idea"},
                             headers=owner_headers, timeout=15)
        assert dec.status_code == 200, dec.text
        assert dec.json()["status"] == "approved"


# ---------------- Reports ----------------
class TestReports:
    def test_overview_has_no_banner_fields(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/reports/overview", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        for banned in ("banner_proposals", "tv_proposals", "campaigns",
                       "sponsorships", "inventory"):
            assert banned not in data, f"Reports overview leaks legacy key '{banned}'"
        for k in ("applications", "partner_submissions", "project_library"):
            assert k in data


# ---------------- Representatives ----------------
class TestRepresentatives:
    def test_list_has_application_stats_only(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/admin/representatives", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        reps = r.json()
        assert isinstance(reps, list) and len(reps) > 0
        rep = reps[0]
        for k in ("applications_total", "applications_approved", "partner_submissions_total"):
            assert k in rep, f"Missing rep stat '{k}'"
        for banned in ("active_engagements", "pending_offers", "approved_offers"):
            assert banned not in rep

    def test_profile_shape(self, owner_headers):
        reps = requests.get(f"{BASE_URL}/api/admin/representatives", headers=owner_headers, timeout=15).json()
        rid = reps[0]["id"]
        r = requests.get(f"{BASE_URL}/api/admin/representatives/{rid}/profile",
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        p = r.json()
        for k in ("stats", "applications", "partner_submissions", "timeline", "notifications"):
            assert k in p, f"Missing profile key '{k}'"
        for banned in ("banner_stats", "tv_stats", "active_campaigns"):
            assert banned not in p


# ---------------- System health ----------------
class TestSystemHealth:
    def test_health_counts(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/admin/system/health", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        counts = r.json().get("database", {}).get("counts", {})
        for k in ("categories", "tv_projects", "productions", "proposals",
                  "audit_entries", "notifications"):
            assert k in counts, f"Missing count '{k}'"
        for banned in ("campaigns", "sponsorships", "banner_inventory", "inventory"):
            assert banned not in counts


# ---------------- Legacy endpoints (must be 404) ----------------
class TestLegacyRemoved:
    @pytest.mark.parametrize("path", ["/api/campaigns", "/api/sponsorships",
                                       "/api/inventory"])
    def test_legacy_gone(self, path, owner_headers):
        r = requests.get(f"{BASE_URL}{path}", headers=owner_headers, timeout=15)
        assert r.status_code == 404, f"{path} should be 404 but got {r.status_code}"


# ---------------- Demo seed (owner-only) ----------------
class TestDemoSeed:
    def test_demo_seed_owner(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/admin/demo/seed", headers=owner_headers, timeout=60)
        assert r.status_code == 200, r.text
        summary = r.json()
        assert isinstance(summary, dict)

    def test_demo_seed_forbidden_for_rep(self, rep_headers):
        r = requests.post(f"{BASE_URL}/api/admin/demo/seed", headers=rep_headers, timeout=30)
        assert r.status_code in (401, 403)
