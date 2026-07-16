"""Iteration 18 backend tests — Representatives CRM upgrade + removeChild fix."""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://agency-operations-1.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
VICTOR = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}


def _login(session: requests.Session, creds: dict) -> dict:
    r = session.post(f"{BASE}/api/auth/login", json=creds)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    _login(s, ADMIN)
    return s


@pytest.fixture(scope="module")
def victor_id(admin_session):
    r = admin_session.get(f"{BASE}/api/admin/representatives")
    assert r.status_code == 200
    for u in r.json():
        if u["email"] == VICTOR["email"]:
            return u["id"]
    pytest.skip("victor not seeded")


# --- 1. list_reps enrichment ---
def test_list_reps_enriched_with_aggregates(admin_session):
    r = admin_session.get(f"{BASE}/api/admin/representatives")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) > 0
    victor = next((u for u in rows if u["email"] == VICTOR["email"]), None)
    assert victor is not None, "Victor not present"
    for f in ("active_engagements", "pending_offers", "approved_offers", "last_activity_at"):
        assert f in victor, f"missing enrichment field {f}"
    # active engagements should exist per PM brief
    assert isinstance(victor["active_engagements"], int)
    assert isinstance(victor["pending_offers"], int)
    assert isinstance(victor["approved_offers"], int)
    # per main-agent smoke: active=8/pending=9/approved=12 range (soft)
    assert victor["approved_offers"] > 0
    assert victor["pending_offers"] > 0
    assert victor["active_engagements"] > 0
    # no password_hash
    assert "password_hash" not in victor


# --- 2. create rep with phone/website/territory ---
def test_create_rep_persists_optional_fields(admin_session):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "email": f"TEST_marco_{unique}@test.example",
        "password": "Test123!",
        "name": "Marco Rossi",
        "agency_name": "Milano Media",
        "country": "IT",
        "phone": "+39 02 1234 5678",
        "website": "https://milano.example",
        "territory": "Lombardy",
        "is_active": True,
    }
    r = admin_session.post(f"{BASE}/api/admin/representatives", json=payload)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert "password_hash" not in body
    assert body["phone"] == payload["phone"]
    assert body["website"] == payload["website"]
    assert body["territory"] == payload["territory"]
    assert body["email"] == payload["email"].lower()
    # verify persistence via GET list
    listing = admin_session.get(f"{BASE}/api/admin/representatives").json()
    found = next((u for u in listing if u["id"] == body["id"]), None)
    assert found is not None
    # cleanup
    admin_session.delete(f"{BASE}/api/admin/representatives/{body['id']}")


# --- 3. profile includes notifications and timeline enrichment ---
def test_profile_includes_notifications_and_timeline_actor(admin_session, victor_id):
    r = admin_session.get(f"{BASE}/api/admin/representatives/{victor_id}/profile")
    assert r.status_code == 200
    data = r.json()
    assert "notifications" in data
    assert isinstance(data["notifications"], list)
    assert "timeline" in data
    assert "representative" in data
    # timeline entries include actor_name/actor_role keys
    for t in data["timeline"][:5]:
        assert "actor_name" in t
        assert "actor_role" in t


# --- 4. PATCH accepts phone/website/territory ---
def test_patch_rep_updates_phone(admin_session, victor_id):
    new_phone = "+33 1 42 00 00 00"
    r = admin_session.patch(f"{BASE}/api/admin/representatives/{victor_id}", json={"phone": new_phone})
    assert r.status_code == 200, r.text
    # verify read-back
    profile = admin_session.get(f"{BASE}/api/admin/representatives/{victor_id}/profile").json()
    assert profile["representative"]["phone"] == new_phone


# --- 5. login updates last_login_at ---
def test_login_updates_last_login_at(admin_session, victor_id):
    # login as Victor in a separate session
    vs = requests.Session()
    _login(vs, VICTOR)
    # give backend a moment
    time.sleep(1)
    profile = admin_session.get(f"{BASE}/api/admin/representatives/{victor_id}/profile").json()
    lla = profile["representative"].get("last_login_at")
    assert lla, "last_login_at not set"
    dt = datetime.fromisoformat(lla.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - dt
    assert delta < timedelta(minutes=2), f"last_login_at not recent: {lla} (delta {delta})"
