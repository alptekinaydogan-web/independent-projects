"""Iteration 6 backend tests — negotiated-offer commercial proposal workflow.

Covers:
  - Inventory catalog (9 networks × 10 positions = 90 items)
  - Banner proposal lifecycle (submit + approve/reject/revision + validation)
  - TV sponsorship proposal lifecycle (submit + episode-conflict semantics)
  - No revenue fields in responses (campaigns/sponsorships/reports/tv-projects)
  - Reports overview count-based shape
  - Confidentiality: rep A cannot see rep B's proposals
"""
import os
import uuid
from datetime import date, timedelta

import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].splitlines()[0]).rstrip("/")
API = f"{BASE_URL}/api"

OWNER = ("admin@independentmedia.hub", "Admin2026!")
REP1 = ("victor.laurent@parismedia.fr", "Rep2026!")
REP2 = ("amelia.hart@londonhouse.co.uk", "Rep2026!")

FORBIDDEN_REVENUE_FIELDS = {
    "internal_cost_usd", "client_total_price_usd", "margin_usd",
    "campaigns_client_revenue_usd", "tv_client_revenue_usd",
    "campaigns_margin_usd", "tv_margin_usd", "top_countries",
    "price_per_episode_usd",
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def owner_token():
    return _login(*OWNER)


@pytest.fixture(scope="module")
def rep1_token():
    return _login(*REP1)


@pytest.fixture(scope="module")
def rep2_token():
    return _login(*REP2)


# ---------- Inventory catalog ----------
class TestInventoryCatalog:
    def test_inventory_shape(self, rep1_token):
        r = requests.get(f"{API}/inventory", headers=_h(rep1_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data["networks"]) == 9
        assert len(data["positions"]) == 10
        assert len(data["items"]) == 90
        keys = {n["key"] for n in data["networks"]}
        assert keys >= {"global", "tourism", "health", "real_estate", "education",
                        "economy", "sports", "technology", "entertainment"}
        pkeys = {p["key"] for p in data["positions"]}
        assert pkeys == {"hero", "header", "sidebar_top", "sidebar_bottom", "article_top",
                         "article_middle", "article_bottom", "footer", "mobile", "sticky"}
        sample = data["items"][0]
        assert sample["id"] == f"{sample['network_key']}__{sample['position_key']}"
        for it in data["items"]:
            for f in FORBIDDEN_REVENUE_FIELDS:
                assert f not in it, f"Forbidden field {f} in inventory item"


# ---------- Banner proposal lifecycle ----------
class TestBannerProposal:
    def test_submit_and_approve_flow(self, rep1_token, owner_token):
        payload = {
            "proposal_name": f"TEST_banner_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_client_ABC",
            "inventory_id": "tourism__hero",
            "offer_amount_usd": 12500.0,
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=30)).isoformat(),
            "impressions": 500000,
            "notes": "iteration6 test proposal",
        }
        r = requests.post(f"{API}/campaigns", headers=_h(rep1_token), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["status"] == "pending_review"
        assert p["network_key"] == "tourism"
        assert p["position_key"] == "hero"
        assert p["network_name"] == "Tourism Network"
        assert p["position_name"] == "Hero Banner"
        assert p["offer_amount_usd"] == 12500.0
        for f in FORBIDDEN_REVENUE_FIELDS:
            assert f not in p, f"Forbidden {f} in campaign response"
        proposal_id = p["id"]

        # Admin sees it in list
        r2 = requests.get(f"{API}/campaigns", headers=_h(owner_token), timeout=15)
        assert r2.status_code == 200
        ids = [x["id"] for x in r2.json()]
        assert proposal_id in ids

        # Admin approves
        r3 = requests.patch(f"{API}/campaigns/{proposal_id}/decision",
                            headers=_h(owner_token),
                            json={"decision": "approved", "admin_notes": "TEST approved"},
                            timeout=15)
        assert r3.status_code == 200
        updated = r3.json()
        assert updated["status"] == "approved"
        assert updated["admin_notes"] == "TEST approved"
        assert updated["decided_at"]

        # Same-status decision is a no-op (returns 200)
        r4 = requests.patch(f"{API}/campaigns/{proposal_id}/decision",
                            headers=_h(owner_token),
                            json={"decision": "approved"}, timeout=15)
        assert r4.status_code == 200

    def test_unknown_inventory_id_400(self, rep1_token):
        r = requests.post(f"{API}/campaigns", headers=_h(rep1_token),
                          json={"proposal_name": "TEST_bad", "client_reference": "x",
                                "inventory_id": "does_not_exist__xxx",
                                "offer_amount_usd": 100.0}, timeout=15)
        assert r.status_code == 400

    def test_zero_offer_400(self, rep1_token):
        r = requests.post(f"{API}/campaigns", headers=_h(rep1_token),
                          json={"proposal_name": "TEST_zero", "client_reference": "x",
                                "inventory_id": "global__hero", "offer_amount_usd": 0}, timeout=15)
        assert r.status_code == 400

    def test_bad_date_range_400(self, rep1_token):
        r = requests.post(f"{API}/campaigns", headers=_h(rep1_token),
                          json={"proposal_name": "TEST_baddate", "client_reference": "x",
                                "inventory_id": "global__hero", "offer_amount_usd": 100.0,
                                "start_date": "2026-06-01", "end_date": "2026-01-01"}, timeout=15)
        assert r.status_code == 400

    def test_revision_requested_flow(self, rep1_token, owner_token):
        r = requests.post(f"{API}/campaigns", headers=_h(rep1_token),
                          json={"proposal_name": f"TEST_rev_{uuid.uuid4().hex[:5]}",
                                "client_reference": "x",
                                "inventory_id": "health__sidebar_top",
                                "offer_amount_usd": 3200.0}, timeout=15)
        pid = r.json()["id"]
        r2 = requests.patch(f"{API}/campaigns/{pid}/decision", headers=_h(owner_token),
                            json={"decision": "revision_requested",
                                  "admin_notes": "please increase impressions"}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["status"] == "revision_requested"

    def test_rep_isolation(self, rep1_token, rep2_token):
        # Rep1 submits
        r = requests.post(f"{API}/campaigns", headers=_h(rep1_token),
                          json={"proposal_name": f"TEST_iso_{uuid.uuid4().hex[:5]}",
                                "client_reference": "iso",
                                "inventory_id": "economy__footer",
                                "offer_amount_usd": 500.0}, timeout=15)
        pid = r.json()["id"]
        # Rep2 must not see it
        r2 = requests.get(f"{API}/campaigns", headers=_h(rep2_token), timeout=15)
        assert r2.status_code == 200
        ids = [x["id"] for x in r2.json()]
        assert pid not in ids, "Rep2 must NOT see rep1's proposal"


# ---------- TV sponsorship proposal lifecycle ----------
class TestSponsorshipProposal:
    @pytest.fixture(scope="class")
    def tv_project(self, owner_token):
        payload = {
            "title": f"TEST_TV_{uuid.uuid4().hex[:5]}",
            "synopsis": "iter6 test", "total_episodes": 12,
            "status": "active",
        }
        r = requests.post(f"{API}/admin/tv-projects", headers=_h(owner_token), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert "price_per_episode_usd" not in doc
        yield doc
        requests.delete(f"{API}/admin/tv-projects/{doc['id']}", headers=_h(owner_token), timeout=15)

    def test_no_price_field_on_tv_project(self, owner_token, tv_project):
        r = requests.get(f"{API}/tv-projects", headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        for p in r.json():
            for f in FORBIDDEN_REVENUE_FIELDS:
                assert f not in p, f"Forbidden {f} on tv project"
            assert "sponsored_episodes" in p
            assert "pending_review_count" in p

    def test_submit_and_approve(self, rep1_token, owner_token, tv_project):
        r = requests.post(f"{API}/sponsorships", headers=_h(rep1_token),
                          json={"tv_project_id": tv_project["id"],
                                "proposal_name": "TEST_sp_1", "client_reference": "sp",
                                "episode_numbers": [1, 2], "offer_amount_usd": 25000.0}, timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["status"] == "pending_review"
        for f in FORBIDDEN_REVENUE_FIELDS:
            assert f not in p
        pid = p["id"]

        r2 = requests.patch(f"{API}/sponsorships/{pid}/decision",
                            headers=_h(owner_token),
                            json={"decision": "approved"}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["status"] == "approved"

    def test_pending_can_compete_but_approved_blocks(self, rep1_token, rep2_token, owner_token, tv_project):
        # Rep1 pending on ep 5
        r1 = requests.post(f"{API}/sponsorships", headers=_h(rep1_token),
                           json={"tv_project_id": tv_project["id"],
                                 "proposal_name": "TEST_a", "client_reference": "a",
                                 "episode_numbers": [5], "offer_amount_usd": 1000}, timeout=15)
        assert r1.status_code == 200
        p1 = r1.json()["id"]
        # Rep2 also pending on ep 5 — should be allowed
        r2 = requests.post(f"{API}/sponsorships", headers=_h(rep2_token),
                           json={"tv_project_id": tv_project["id"],
                                 "proposal_name": "TEST_b", "client_reference": "b",
                                 "episode_numbers": [5], "offer_amount_usd": 2000}, timeout=15)
        assert r2.status_code == 200, f"pending should not conflict: {r2.text}"
        p2 = r2.json()["id"]
        # Admin approves p1
        ra = requests.patch(f"{API}/sponsorships/{p1}/decision", headers=_h(owner_token),
                            json={"decision": "approved"}, timeout=15)
        assert ra.status_code == 200
        # Now approving p2 should 409
        rb = requests.patch(f"{API}/sponsorships/{p2}/decision", headers=_h(owner_token),
                            json={"decision": "approved"}, timeout=15)
        assert rb.status_code == 409, f"expected conflict, got {rb.status_code}: {rb.text}"

    def test_zero_offer_400(self, rep1_token, tv_project):
        r = requests.post(f"{API}/sponsorships", headers=_h(rep1_token),
                          json={"tv_project_id": tv_project["id"],
                                "proposal_name": "TEST_zero", "client_reference": "z",
                                "episode_numbers": [10], "offer_amount_usd": 0}, timeout=15)
        assert r.status_code == 400

    def test_rep_isolation_sponsorships(self, rep1_token, rep2_token, tv_project):
        r1 = requests.post(f"{API}/sponsorships", headers=_h(rep1_token),
                           json={"tv_project_id": tv_project["id"],
                                 "proposal_name": "TEST_iso_sp", "client_reference": "iso",
                                 "episode_numbers": [11], "offer_amount_usd": 100}, timeout=15)
        pid = r1.json()["id"]
        r2 = requests.get(f"{API}/sponsorships", headers=_h(rep2_token), timeout=15)
        ids = [x["id"] for x in r2.json()]
        assert pid not in ids


# ---------- Reports overview shape ----------
class TestReportsOverview:
    def test_admin_shape(self, owner_token):
        r = requests.get(f"{API}/reports/overview", headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        for f in FORBIDDEN_REVENUE_FIELDS:
            assert f not in d, f"Forbidden {f} in reports.overview"
        assert set(["banner_proposals", "tv_proposals", "editorial_proposals",
                    "monthly_series", "top_networks", "inventory_products_count",
                    "total_reps_active", "all_pending_review", "role"]).issubset(d.keys())
        assert d["inventory_products_count"] == 90
        for k in ("pending_review", "approved", "rejected", "revision_requested", "total"):
            assert k in d["banner_proposals"]
            assert k in d["tv_proposals"]
        # monthly_series shape
        for m in d["monthly_series"]:
            assert set(m.keys()) >= {"month", "banner_submitted", "banner_approved",
                                     "tv_submitted", "tv_approved"}

    def test_rep_shape(self, rep1_token):
        r = requests.get(f"{API}/reports/overview", headers=_h(rep1_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        for f in FORBIDDEN_REVENUE_FIELDS:
            assert f not in d
        assert "total_reps_active" not in d
        assert "all_pending_review" not in d
