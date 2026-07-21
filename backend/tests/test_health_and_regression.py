"""Health endpoint + regression tests for iteration 26."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://agency-operations-1.preview.emergentagent.com").rstrip("/")
LOCAL_URL = "http://127.0.0.1:8001"

OWNER = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}

EXPECTED_BODY = {"status": "ok", "service": "independent-commerce"}


# ---------- Health endpoints ----------
@pytest.mark.parametrize("path", ["/api/health", "/health", "/healthz"])
def test_health_local(path):
    """All 3 aliases must return 200 with expected body when hit directly on backend
    (this is what Docker HEALTHCHECK / nginx proxy in Coolify will see)."""
    r = requests.get(f"{LOCAL_URL}{path}", timeout=5)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    assert r.json() == EXPECTED_BODY


def test_health_public_ingress():
    """Public ingress only routes /api/* to backend — /api/health must work."""
    r = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert r.status_code == 200
    assert r.json() == EXPECTED_BODY


def test_health_no_auth_required():
    r = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert r.status_code == 200
    assert "Authorization" not in r.request.headers


# ---------- Regression: auth + core endpoints ----------
@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER, timeout=15)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def rep_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=REP, timeout=15)
    assert r.status_code == 200, f"Rep login failed: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


def test_owner_login(owner_token):
    assert owner_token


def test_rep_login(rep_token):
    assert rep_token


def test_tv_projects_list(rep_token):
    r = requests.get(f"{BASE_URL}/api/tv-projects",
                     headers={"Authorization": f"Bearer {rep_token}"}, timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), (list, dict))


def test_admin_system_health(owner_token):
    r = requests.get(f"{BASE_URL}/api/admin/system/health",
                     headers={"Authorization": f"Bearer {owner_token}"}, timeout=15)
    assert r.status_code == 200
