"""Iteration 19 — Independent Projects pivot backend tests."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://agency-operations-1.preview.emergentagent.com"
ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def rep_s():
    return _login(REP)


@pytest.fixture(scope="module")
def active_project_id(admin_s):
    r = admin_s.get(f"{BASE}/api/tv-projects?status=active", timeout=15)
    assert r.status_code == 200
    items = r.json()
    assert items, "No active TV projects found"
    return items[0]["id"]


def test_apply_to_produce_first_and_duplicate(rep_s, admin_s, active_project_id):
    # Clean any existing production for this rep+project so test is repeatable
    apps = rep_s.get(f"{BASE}/api/my-productions", timeout=15).json()
    already = any(a.get("tv_project_id") == active_project_id for a in apps)

    body = {"tv_project_id": active_project_id,
            "message": "TEST_iter19 application",
            "target_launch_date": "2026-06-01"}
    r1 = rep_s.post(f"{BASE}/api/tv-projects/{active_project_id}/apply", json=body, timeout=15)
    if already:
        assert r1.status_code == 409
        assert "already applied" in r1.json().get("detail", "").lower()
    else:
        assert r1.status_code == 200, r1.text
        data = r1.json()
        assert data["status"] == "submitted"
        assert data["tv_project_id"] == active_project_id
        assert data["rep_id"]
        assert "tv_project_title" in data
        assert "agency_name" in data
        assert "country" in data
        assert data["message"] == "TEST_iter19 application"
        # duplicate returns 409
        r2 = rep_s.post(f"{BASE}/api/tv-projects/{active_project_id}/apply", json=body, timeout=15)
        assert r2.status_code == 409
        assert "already applied" in r2.json().get("detail", "").lower()


def test_my_productions_contains_application(rep_s, active_project_id):
    r = rep_s.get(f"{BASE}/api/my-productions", timeout=15)
    assert r.status_code == 200
    apps = r.json()
    assert any(a["tv_project_id"] == active_project_id for a in apps)


def test_admin_list_applications(admin_s, active_project_id):
    r = admin_s.get(f"{BASE}/api/tv-projects/{active_project_id}/applications", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(a["tv_project_id"] == active_project_id for a in data)


def test_apply_to_inactive_project(admin_s, rep_s):
    # Create draft project, apply → 400
    payload = {"title": "TEST_iter19 Inactive", "synopsis": "test",
               "total_episodes": 4, "duration_minutes": 30,
               "status": "draft"}
    c = admin_s.post(f"{BASE}/api/admin/tv-projects", json=payload, timeout=15)
    assert c.status_code == 200, c.text
    pid = c.json()["id"]
    try:
        r = rep_s.post(f"{BASE}/api/tv-projects/{pid}/apply",
                        json={"tv_project_id": pid, "message": "x", "target_launch_date": ""},
                        timeout=15)
        assert r.status_code == 400
        assert "not open for new productions" in r.json().get("detail", "").lower()
    finally:
        admin_s.delete(f"{BASE}/api/admin/tv-projects/{pid}", timeout=15)


def test_regression_campaigns_endpoint(admin_s):
    r = admin_s.get(f"{BASE}/api/campaigns", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_regression_banner_inventory_endpoint(admin_s):
    # Banner routes still respond (backwards compat)
    r = admin_s.get(f"{BASE}/api/inventory", timeout=15)
    assert r.status_code in (200, 404)  # accept either — just not 500


def test_tv_project_detail_has_expected_fields(rep_s, active_project_id):
    r = rep_s.get(f"{BASE}/api/tv-projects/{active_project_id}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == active_project_id
    assert d["status"] == "active"
    assert "title" in d
