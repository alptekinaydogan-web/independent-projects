"""Iteration 7 backend tests — lifecycle history + split notes + duplicate + archive + CSV export."""
import os
import io
import csv
import time
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP1 = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}
REP2 = {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login {creds['email']}: {r.status_code} {r.text}"
    data = r.json()
    s.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    return s, data["user"]


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def rep():
    return _login(REP1)


@pytest.fixture(scope="module")
def rep2():
    return _login(REP2)


def _get_inv_item(sess):
    r = sess.get(f"{API}/inventory", timeout=15)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    return items[0]


@pytest.fixture(scope="module")
def inventory_item(rep):
    s, _ = rep
    return _get_inv_item(s)


@pytest.fixture(scope="module")
def tv_project(rep):
    s, _ = rep
    projects = s.get(f"{API}/tv-projects", timeout=15).json()
    active = [p for p in projects if p.get("status", "active") == "active"]
    assert active, "Need at least one active TV project"
    return active[0]


def _create_banner(rep_sess, inv_item, name_suffix=""):
    payload = {
        "proposal_name": f"TEST_it7_banner_{name_suffix}_{uuid.uuid4().hex[:6]}",
        "client_reference": "TEST_ref",
        "inventory_id": inv_item["id"],
        "impressions": 50000,
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
        "offer_amount_usd": 1500.0,
        "notes": "initial",
    }
    r = rep_sess.post(f"{API}/campaigns", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _create_sponsorship(rep_sess, project, name_suffix=""):
    # sponsored_episodes may be list[int] (from list) or list[dict] (from detail)
    taken = set()
    for e in project.get("sponsored_episodes", []) or []:
        if isinstance(e, dict):
            taken.add(e.get("episode"))
        else:
            taken.add(e)
    ep = next(e for e in range(1, project["total_episodes"] + 1) if e not in taken)
    payload = {
        "proposal_name": f"TEST_it7_tv_{name_suffix}_{uuid.uuid4().hex[:6]}",
        "client_reference": "TEST_ref",
        "tv_project_id": project["id"],
        "episode_numbers": [ep],
        "offer_amount_usd": 2500.0,
        "notes": "initial tv",
    }
    r = rep_sess.post(f"{API}/sponsorships", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- Banner split notes ----------------
class TestBannerSplitNotes:
    def test_decision_with_split_notes(self, admin, rep):
        s_admin, _ = admin
        s_rep, rep_user = rep
        # Get fresh inventory
        inv_item = _get_inv_item(s_rep)
        p = _create_banner(s_rep, inv_item, "split")
        pid = p["id"]

        rep_msg = "Please increase offer to $2000"
        internal_msg = "Client seems low-value; consider rejecting if not revised"
        r = s_admin.patch(f"{API}/campaigns/{pid}/decision", json={
            "decision": "revision_requested",
            "representative_feedback": rep_msg,
            "internal_notes": internal_msg,
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # Admin sees both
        assert data["representative_feedback"] == rep_msg
        assert data["internal_notes"] == internal_msg
        assert data["status"] == "revision_requested"
        assert isinstance(data.get("history"), list)
        # history has entry with both
        rev_entries = [h for h in data["history"] if h["status"] == "revision_requested"]
        assert rev_entries, "revision_requested history entry missing"
        assert rev_entries[-1]["representative_feedback"] == rep_msg
        assert rev_entries[-1]["internal_notes"] == internal_msg

        # Rep view - strip internal
        r_rep = s_rep.get(f"{API}/campaigns/{pid}", timeout=15)
        assert r_rep.status_code == 200
        rep_data = r_rep.json()
        assert "internal_notes" not in rep_data, f"internal_notes leaked at top-level: {rep_data}"
        assert rep_data["representative_feedback"] == rep_msg
        for h in rep_data.get("history", []):
            assert "internal_notes" not in h, f"internal_notes leaked in history entry: {h}"


# ---------------- TV split notes ----------------
class TestTVSplitNotes:
    def test_decision_with_split_notes(self, admin, rep, tv_project):
        s_admin, _ = admin
        s_rep, _ = rep
        # Reload project to have current taken episodes
        proj = s_rep.get(f"{API}/tv-projects/{tv_project['id']}", timeout=15).json()
        # Note: get returns list of dicts for sponsored_episodes
        p = _create_sponsorship(s_rep, proj, "split")
        pid = p["id"]

        rep_msg = "Please adjust to 2 episodes"
        internal_msg = "Sponsor is niche; low internal priority"
        r = s_admin.patch(f"{API}/sponsorships/{pid}/decision", json={
            "decision": "revision_requested",
            "representative_feedback": rep_msg,
            "internal_notes": internal_msg,
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["representative_feedback"] == rep_msg
        assert data["internal_notes"] == internal_msg
        rev = [h for h in data["history"] if h["status"] == "revision_requested"]
        assert rev and rev[-1]["internal_notes"] == internal_msg

        # Rep view stripped
        r_rep = s_rep.get(f"{API}/sponsorships/{pid}", timeout=15)
        rep_data = r_rep.json()
        assert "internal_notes" not in rep_data
        for h in rep_data.get("history", []):
            assert "internal_notes" not in h


# ---------------- Banner duplicate ----------------
class TestBannerDuplicate:
    def test_duplicate_after_revision_request(self, admin, rep):
        s_admin, _ = admin
        s_rep, _ = rep
        inv_item = _get_inv_item(s_rep)
        parent = _create_banner(s_rep, inv_item, "dup")
        pid = parent["id"]

        # Admin requests revision
        r = s_admin.patch(f"{API}/campaigns/{pid}/decision", json={
            "decision": "revision_requested",
            "representative_feedback": "Please revise offer",
            "internal_notes": "quiet_admin_note",
        }, timeout=15)
        assert r.status_code == 200

        # Rep duplicates with override
        override = {"offer_amount_usd": 2500.0, "notes": "Revised per feedback"}
        r_dup = s_rep.post(f"{API}/campaigns/{pid}/duplicate", json=override, timeout=15)
        assert r_dup.status_code == 200, r_dup.text
        new = r_dup.json()
        assert new["status"] == "revised"
        assert new["parent_proposal_id"] == pid
        assert new["offer_amount_usd"] == 2500.0
        assert new["notes"] == "Revised per feedback"
        # Inherited fields
        assert new["inventory_id"] == parent["inventory_id"]
        assert new["campaign_name"] == parent["campaign_name"]
        # history contains revised entry
        statuses = [h["status"] for h in new.get("history", [])]
        assert "revised" in statuses
        # No internal_notes for rep
        assert "internal_notes" not in new
        for h in new.get("history", []):
            assert "internal_notes" not in h

        # Original proposal still revision_requested
        orig = s_rep.get(f"{API}/campaigns/{pid}", timeout=15).json()
        assert orig["status"] == "revision_requested"

    def test_rep_cannot_duplicate_others_proposal(self, admin, rep, rep2):
        s_rep, _ = rep
        s_rep2, _ = rep2
        inv_item = _get_inv_item(s_rep)
        parent = _create_banner(s_rep, inv_item, "dup_forbid")
        r = s_rep2.post(f"{API}/campaigns/{parent['id']}/duplicate", json={}, timeout=15)
        assert r.status_code == 403


# ---------------- TV duplicate ----------------
class TestTVDuplicate:
    def test_duplicate_inherits_episodes(self, admin, rep, tv_project):
        s_admin, _ = admin
        s_rep, _ = rep
        proj = s_rep.get(f"{API}/tv-projects/{tv_project['id']}", timeout=15).json()
        parent = _create_sponsorship(s_rep, proj, "dup")
        pid = parent["id"]

        # Admin requests revision
        r = s_admin.patch(f"{API}/sponsorships/{pid}/decision", json={
            "decision": "revision_requested",
            "representative_feedback": "please tweak",
        }, timeout=15)
        assert r.status_code == 200

        # Duplicate with only offer override
        r_dup = s_rep.post(f"{API}/sponsorships/{pid}/duplicate",
                           json={"offer_amount_usd": 3333.0}, timeout=15)
        assert r_dup.status_code == 200, r_dup.text
        new = r_dup.json()
        assert new["status"] == "revised"
        assert new["parent_proposal_id"] == pid
        assert new["offer_amount_usd"] == 3333.0
        # Episodes inherited
        assert new["episode_numbers"] == parent["episode_numbers"]


# ---------------- Archive / Unarchive ----------------
class TestArchive:
    def test_manual_archive_and_unarchive(self, admin, rep):
        s_admin, _ = admin
        s_rep, _ = rep
        inv_item = _get_inv_item(s_rep)
        p = _create_banner(s_rep, inv_item, "archive")
        pid = p["id"]

        # Archive
        r = s_admin.post(f"{API}/campaigns/{pid}/archive",
                         json={"reason": "TEST cleanup"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_archived"] is True
        assert d["archived_at"]
        assert any(h["status"] == "archived" for h in d.get("history", []))

        # List without include_archived — should NOT include
        listing = s_admin.get(f"{API}/campaigns", timeout=15).json()
        assert not any(c["id"] == pid for c in listing), "archived proposal leaked in default listing"

        # List with include_archived=true — should include
        listing_all = s_admin.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
        assert any(c["id"] == pid for c in listing_all)

        # Unarchive
        r_un = s_admin.post(f"{API}/campaigns/{pid}/unarchive", timeout=15)
        assert r_un.status_code == 200
        du = r_un.json()
        assert du["is_archived"] is False
        assert any(h["status"] == "unarchived" for h in du.get("history", []))


# ---------------- CSV export ----------------
class TestCSVExport:
    EXPECTED_COLUMNS = [
        "kind", "proposal_id", "parent_proposal_id", "status", "is_archived",
        "created_at", "decided_at", "archived_at",
        "rep_name", "agency_name", "client_reference", "proposal_name",
        "inventory_network", "inventory_position", "tv_project_title",
        "episodes", "impressions", "start_date", "end_date",
        "offer_amount_usd",
        "representative_feedback", "internal_notes",
        "last_decision_actor", "history_length",
    ]

    def test_admin_csv_export(self, admin):
        s, _ = admin
        month = time.strftime("%Y-%m")
        r = s.get(f"{API}/reports/proposals/export.csv",
                  params={"month": month, "kind": "all", "include_archived": "true"},
                  timeout=30)
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "").lower()
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert ".csv" in cd.lower()
        # Parse CSV
        text = r.text
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert rows, "empty CSV"
        header = rows[0]
        assert header == self.EXPECTED_COLUMNS, f"Header mismatch: {header}"
        assert len(header) == 24

    def test_non_admin_forbidden(self, rep):
        s, _ = rep
        r = s.get(f"{API}/reports/proposals/export.csv", timeout=15)
        assert r.status_code == 403

    def test_csv_no_month_filter(self, admin):
        s, _ = admin
        r = s.get(f"{API}/reports/proposals/export.csv", params={"kind": "banner"}, timeout=30)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "").lower()


# ---------------- Rep privacy contract ----------------
class TestRepPrivacy:
    def test_no_internal_notes_in_lists(self, rep, admin):
        s_rep, _ = rep
        s_admin, _ = admin
        # Ensure at least one proposal has internal notes
        inv_item = _get_inv_item(s_rep)
        p = _create_banner(s_rep, inv_item, "privacy")
        s_admin.patch(f"{API}/campaigns/{p['id']}/decision", json={
            "decision": "revision_requested",
            "representative_feedback": "public",
            "internal_notes": "SECRET_ADMIN_ONLY_XYZ",
        }, timeout=15)

        # Rep list
        listing = s_rep.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
        for c in listing:
            assert "internal_notes" not in c, f"internal_notes in list record {c.get('id')}"
            for h in c.get("history", []) or []:
                assert "internal_notes" not in h, f"internal_notes in history of {c.get('id')}"

        # Rep GET one
        one = s_rep.get(f"{API}/campaigns/{p['id']}", timeout=15).json()
        assert "internal_notes" not in one
        # Also confirm the secret string does not appear anywhere in serialized response
        import json as _json
        assert "SECRET_ADMIN_ONLY_XYZ" not in _json.dumps(one)

    def test_no_internal_notes_in_sponsorship_lists(self, rep):
        s_rep, _ = rep
        listing = s_rep.get(f"{API}/sponsorships?include_archived=true", timeout=15).json()
        for c in listing:
            assert "internal_notes" not in c
            for h in c.get("history", []) or []:
                assert "internal_notes" not in h
