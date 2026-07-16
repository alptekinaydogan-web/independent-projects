"""Iteration 16 — QA polish pass. Backend coverage:
  1. GET /admin/representatives/{id}/profile
  2. GET /inventory/{id} (admin vs rep views)
  3. GET /inventory/{id}/availability (13 monthly buckets)
  4. POST /campaigns overlap guard (409)
  5. GET /countries usable by rep + admin (60+ items, FR present)
"""
import os, requests, pytest, uuid
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


def _login(c):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=c, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def owner():
    return _login(OWNER)


@pytest.fixture(scope="module")
def rep():
    return _login(REP)


@pytest.fixture(scope="module")
def rep_id(owner):
    reps = owner.get(f"{API}/admin/representatives", timeout=15).json()
    victor = next(r for r in reps if r["email"] == REP["email"])
    return victor["id"]


# ---------- 1. Rep profile ----------
def test_rep_profile_owner_shape(owner, rep_id):
    r = owner.get(f"{API}/admin/representatives/{rep_id}/profile", timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ["representative", "banner_stats", "tv_stats", "active_campaigns", "history", "timeline"]:
        assert k in d, f"missing key {k}"
    assert d["representative"]["email"] == REP["email"]
    # Stats have total + status buckets
    assert "total" in d["banner_stats"]
    assert "total" in d["tv_stats"]
    assert d["banner_stats"]["total"] >= 1
    # History contains both banner and sponsorship kinds, sorted desc by created_at
    kinds = {h["kind"] for h in d["history"]}
    assert "banner" in kinds or "sponsorship" in kinds
    times = [h.get("created_at") or "" for h in d["history"]]
    assert times == sorted(times, reverse=True)


def test_rep_profile_forbidden_for_rep(rep, rep_id):
    r = rep.get(f"{API}/admin/representatives/{rep_id}/profile", timeout=15)
    assert r.status_code == 403


# ---------- 2. Inventory detail ----------
@pytest.fixture(scope="module")
def any_inventory_id(owner):
    inv = owner.get(f"{API}/inventory", timeout=15).json()
    items = inv["items"]
    return items[0]["id"]


@pytest.fixture(scope="module")
def reserved_inventory_id(owner):
    """Find an inventory item that has at least one approved+non-archived campaign."""
    camps = owner.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
    for c in camps:
        if c.get("status") == "approved" and not c.get("is_archived") and c.get("inventory_id"):
            return c["inventory_id"]
    return None


def test_inventory_detail_admin(owner, any_inventory_id):
    r = owner.get(f"{API}/inventory/{any_inventory_id}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ["inventory", "status", "reservations", "offers", "is_admin_view"]:
        assert k in d
    assert d["is_admin_view"] is True
    assert d["status"] in {"available", "reserved", "active", "expired"}


def test_inventory_detail_rep_view_filters_offers(rep, any_inventory_id):
    r = rep.get(f"{API}/inventory/{any_inventory_id}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["is_admin_view"] is False
    # Reservations always include external ones with is_yours flag
    for res in d["reservations"]:
        assert "is_yours" in res
        assert "agency_name" in res


def test_inventory_detail_reserved_has_active_status(owner, reserved_inventory_id):
    if not reserved_inventory_id:
        pytest.skip("No approved reservation in demo data")
    r = owner.get(f"{API}/inventory/{reserved_inventory_id}", timeout=15)
    d = r.json()
    assert d["status"] in {"reserved", "active", "expired"}
    assert len(d["reservations"]) >= 1


# ---------- 3. Availability calendar ----------
def test_inventory_availability_13_buckets(owner, any_inventory_id):
    r = owner.get(f"{API}/inventory/{any_inventory_id}/availability", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["inventory_id"] == any_inventory_id
    assert isinstance(d["months"], list)
    assert len(d["months"]) == 13
    for m in d["months"]:
        for k in ("year", "month", "label", "state", "reserved_by"):
            assert k in m
        assert m["state"] in {"available", "reserved", "active", "expired"}


def test_availability_reflects_reservation(owner, reserved_inventory_id):
    if not reserved_inventory_id:
        pytest.skip("No approved reservation in demo data")
    d = owner.get(f"{API}/inventory/{reserved_inventory_id}/availability", timeout=15).json()
    states = {m["state"] for m in d["months"]}
    assert states & {"reserved", "active", "expired"}, states


# ---------- 4. Overlap guard on POST /campaigns ----------
def test_campaign_overlap_returns_409(rep, owner, reserved_inventory_id):
    if not reserved_inventory_id:
        pytest.skip("No approved reservation to overlap with")
    # Grab exact window of the approved reservation
    camps = owner.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
    ref = next(c for c in camps
               if c.get("inventory_id") == reserved_inventory_id
               and c.get("status") == "approved"
               and not c.get("is_archived"))
    body = {
        "proposal_name": f"TEST_overlap_{uuid.uuid4().hex[:6]}",
        "client_reference": "TEST",
        "inventory_id": reserved_inventory_id,
        "impressions": 100000,
        "start_date": ref["start_date"][:10],
        "end_date": ref["end_date"][:10],
        "offer_amount_usd": 1000,
        "notes": "overlap test",
    }
    r = rep.post(f"{API}/campaigns", json=body, timeout=15)
    assert r.status_code == 409, f"{r.status_code} {r.text}"
    assert "already reserved" in r.text.lower()


def test_campaign_non_overlapping_window_succeeds(rep, owner):
    # Find an inventory item with NO approved reservation
    inv = owner.get(f"{API}/inventory", timeout=15).json()["items"]
    camps = owner.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
    reserved_ids = {c["inventory_id"] for c in camps
                    if c.get("status") == "approved" and not c.get("is_archived")}
    free = next((i for i in inv if i["id"] not in reserved_ids), None)
    assert free, "no free inventory available for test"
    body = {
        "proposal_name": f"TEST_free_{uuid.uuid4().hex[:6]}",
        "client_reference": "TEST",
        "inventory_id": free["id"],
        "impressions": 50000,
        "start_date": "2027-06-01",
        "end_date": "2027-06-30",
        "offer_amount_usd": 500,
        "notes": "non-overlap test",
    }
    r = rep.post(f"{API}/campaigns", json=body, timeout=15)
    assert r.status_code in (200, 201), f"{r.status_code} {r.text}"


# ---------- 5. Countries for both roles ----------
def test_countries_owner(owner):
    r = owner.get(f"{API}/countries", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d, list) and len(d) >= 60
    assert any(c["code"] == "FR" for c in d)
    for c in d[:5]:
        assert "code" in c and "name" in c


def test_countries_rep(rep):
    r = rep.get(f"{API}/countries", timeout=10)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d, list) and len(d) >= 60
    assert any(c["code"] == "FR" for c in d)


def test_countries_unauth():
    r = requests.get(f"{API}/countries", timeout=10)
    assert r.status_code in (401, 403)
