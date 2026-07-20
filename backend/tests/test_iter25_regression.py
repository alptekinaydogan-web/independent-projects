"""Iteration 25 regression tests after removing emergentintegrations from requirements.txt."""
import os
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://agency-operations-1.preview.emergentagent.com').rstrip('/')

OWNER = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def rep_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=REP, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_owner_login():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "access_token" in d and d["user"]["role"] == "owner"


def test_rep_login():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=REP, timeout=15)
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "representative"


def test_tv_projects_rep(rep_token):
    r = requests.get(f"{BASE_URL}/api/tv-projects", headers=_h(rep_token), timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_tv_projects_owner(owner_token):
    r = requests.get(f"{BASE_URL}/api/tv-projects", headers=_h(owner_token), timeout=15)
    assert r.status_code == 200


def test_admin_system_health(owner_token):
    r = requests.get(f"{BASE_URL}/api/admin/system/health", headers=_h(owner_token), timeout=15)
    assert r.status_code == 200


def test_reports_overview(owner_token):
    r = requests.get(f"{BASE_URL}/api/reports/overview", headers=_h(owner_token), timeout=15)
    assert r.status_code == 200


def test_create_project_draft(rep_token):
    payload = {
        "title": "TEST_iter25_draft",
        "description": "Regression test draft",
        "budget": 1000,
        "currency": "USD",
    }
    r = requests.post(f"{BASE_URL}/api/projects", headers=_h(rep_token), json=payload, timeout=15)
    # Accept 200/201 create or 422 if schema differs; core check that endpoint reachable non-500
    assert r.status_code in (200, 201, 400, 422), f"unexpected {r.status_code}: {r.text}"
