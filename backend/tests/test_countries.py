"""Tests for the new GET /api/countries reference endpoint."""
import requests, pytest
from pathlib import Path


def _base():
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    return ""


BASE = _base()
API = BASE + "/api"
OWNER = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def owner():
    return _login(OWNER)


@pytest.fixture(scope="module")
def rep():
    return _login(REP)


def test_countries_owner_200(owner):
    r = owner.get(f"{API}/countries", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list) and len(data) > 0
    codes = {c["code"] for c in data}
    assert {"FR", "GB", "DE"}.issubset(codes)
    for c in data:
        assert "code" in c and "name" in c
        assert isinstance(c["code"], str) and isinstance(c["name"], str)


def test_countries_rep_forbidden(rep):
    r = rep.get(f"{API}/countries", timeout=15)
    assert r.status_code in (401, 403), r.status_code


def test_countries_unauth():
    r = requests.get(f"{API}/countries", timeout=15)
    assert r.status_code in (401, 403), r.status_code
