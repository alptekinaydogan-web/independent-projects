"""Iteration 8 backend tests — Premium PDF proposal generation + sponsorship duplicate episode override."""
import os
import io
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP1 = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}
REP2 = {"email": "amelia.hart@londonhouse.co.uk", "password": "Rep2026!"}

SECRET = "SECRET_ADMIN_LEAK_MARKER_XYZ_9182"


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
    return r.json()["items"][0]


@pytest.fixture(scope="module")
def active_tv_project(rep):
    s, _ = rep
    projects = s.get(f"{API}/tv-projects", timeout=15).json()
    active = [p for p in projects if p.get("status", "active") == "active"]
    assert active, "Need at least one active TV project"
    # Pick project with enough free episodes for parallel test workers
    for p in active:
        detail = s.get(f"{API}/tv-projects/{p['id']}", timeout=15).json()
        taken = set()
        for e in detail.get("sponsored_episodes", []) or []:
            taken.add(e.get("episode") if isinstance(e, dict) else e)
        free = detail["total_episodes"] - len(taken)
        if free >= 12:
            return detail
    # Fallback: return the one with most free
    best = None; best_free = -1
    for p in active:
        detail = s.get(f"{API}/tv-projects/{p['id']}", timeout=15).json()
        taken = set()
        for e in detail.get("sponsored_episodes", []) or []:
            taken.add(e.get("episode") if isinstance(e, dict) else e)
        free = detail["total_episodes"] - len(taken)
        if free > best_free:
            best_free, best = free, detail
    return best


def _taken_eps(project):
    taken = set()
    for e in project.get("sponsored_episodes", []) or []:
        if isinstance(e, dict):
            taken.add(e.get("episode"))
        else:
            taken.add(e)
    return taken


def _next_free_ep(project, exclude=None):
    exclude = exclude or set()
    taken = _taken_eps(project) | exclude
    for e in range(1, project["total_episodes"] + 1):
        if e not in taken:
            return e
    raise RuntimeError("No free episodes")


def _create_approved_banner(rep_sess, admin_sess, inv_item, internal="internal thoughts"):
    payload = {
        "proposal_name": f"TEST_it8_banner_{uuid.uuid4().hex[:6]}",
        "client_reference": "TEST_ref",
        "inventory_id": inv_item["id"],
        "impressions": 50000,
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
        "offer_amount_usd": 1500.0,
        "notes": "for pdf test",
    }
    r = rep_sess.post(f"{API}/campaigns", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    r2 = admin_sess.patch(f"{API}/campaigns/{pid}/decision", json={
        "decision": "approved",
        "representative_feedback": "Approved, ship it",
        "internal_notes": internal,
    }, timeout=15)
    assert r2.status_code == 200, r2.text
    return r2.json()


def _create_pending_banner(rep_sess, inv_item):
    payload = {
        "proposal_name": f"TEST_it8_pending_{uuid.uuid4().hex[:6]}",
        "client_reference": "TEST_ref",
        "inventory_id": inv_item["id"],
        "impressions": 10000,
        "start_date": "2026-02-01",
        "offer_amount_usd": 900.0,
    }
    r = rep_sess.post(f"{API}/campaigns", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _create_sponsorship(rep_sess, project, episodes, offer=2500.0):
    payload = {
        "proposal_name": f"TEST_it8_tv_{uuid.uuid4().hex[:6]}",
        "client_reference": "TEST_ref",
        "tv_project_id": project["id"],
        "episode_numbers": episodes,
        "offer_amount_usd": offer,
        "notes": "for pdf test",
    }
    r = rep_sess.post(f"{API}/sponsorships", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _approve_sponsorship(admin_sess, pid, internal="private internal"):
    r = admin_sess.patch(f"{API}/sponsorships/{pid}/decision", json={
        "decision": "approved",
        "representative_feedback": "Excellent proposal.",
        "internal_notes": internal,
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _request_revision(admin_sess, kind, pid):
    ep = "campaigns" if kind == "banner" else "sponsorships"
    r = admin_sess.patch(f"{API}/{ep}/{pid}/decision", json={
        "decision": "revision_requested",
        "representative_feedback": "pls tweak",
        "internal_notes": "quiet_note",
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


# ==================== BANNER PDF ====================
class TestBannerPDF:
    def test_owning_rep_can_download_approved(self, rep, admin):
        s_rep, _ = rep
        s_admin, _ = admin
        inv = _get_inv_item(s_rep)
        p = _create_approved_banner(s_rep, s_admin, inv, internal=SECRET)
        r = s_rep.get(f"{API}/campaigns/{p['id']}/proposal.pdf", timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        cd = r.headers.get("content-disposition", "")
        assert "inline" in cd.lower()
        assert "IMN-proposal-" in cd
        assert ".pdf" in cd.lower()
        body = r.content
        assert body[:5] == b"%PDF-", f"Missing PDF magic: {body[:10]!r}"
        assert b"%%EOF" in body[-1024:], "Missing %%EOF near end"
        # Privacy: no internal_notes leak
        assert b"internal_notes" not in body
        assert SECRET.encode() not in body, "Internal notes secret leaked in PDF for rep!"

    def test_non_owner_rep_403(self, rep, rep2, admin):
        s_rep, _ = rep
        s_rep2, _ = rep2
        s_admin, _ = admin
        inv = _get_inv_item(s_rep)
        p = _create_approved_banner(s_rep, s_admin, inv)
        r = s_rep2.get(f"{API}/campaigns/{p['id']}/proposal.pdf", timeout=15)
        assert r.status_code == 403

    def test_non_approved_400(self, rep):
        s_rep, _ = rep
        inv = _get_inv_item(s_rep)
        p = _create_pending_banner(s_rep, inv)
        r = s_rep.get(f"{API}/campaigns/{p['id']}/proposal.pdf", timeout=15)
        assert r.status_code == 400

    def test_admin_can_download(self, rep, admin):
        s_rep, _ = rep
        s_admin, _ = admin
        inv = _get_inv_item(s_rep)
        p = _create_approved_banner(s_rep, s_admin, inv, internal=SECRET)
        r = s_admin.get(f"{API}/campaigns/{p['id']}/proposal.pdf", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"

    def test_not_found_404(self, rep):
        s_rep, _ = rep
        r = s_rep.get(f"{API}/campaigns/{uuid.uuid4()}/proposal.pdf", timeout=15)
        assert r.status_code == 404


# ==================== SPONSORSHIP PDF ====================
class TestSponsorshipPDF:
    def test_owning_rep_approved_pdf(self, rep, admin, active_tv_project):
        s_rep, _ = rep
        s_admin, _ = admin
        proj = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        ep = _next_free_ep(proj)
        sp = _create_sponsorship(s_rep, proj, [ep])
        _approve_sponsorship(s_admin, sp["id"], internal=SECRET)
        r = s_rep.get(f"{API}/sponsorships/{sp['id']}/proposal.pdf", timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        cd = r.headers.get("content-disposition", "")
        assert "IMN-sponsorship-" in cd
        body = r.content
        assert body[:5] == b"%PDF-"
        assert b"%%EOF" in body[-1024:]
        assert b"internal_notes" not in body
        assert SECRET.encode() not in body

    def test_pending_400(self, rep, active_tv_project):
        s_rep, _ = rep
        proj = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        ep = _next_free_ep(proj)
        sp = _create_sponsorship(s_rep, proj, [ep])
        r = s_rep.get(f"{API}/sponsorships/{sp['id']}/proposal.pdf", timeout=15)
        assert r.status_code == 400

    def test_admin_download(self, rep, admin, active_tv_project):
        s_rep, _ = rep
        s_admin, _ = admin
        proj = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        ep = _next_free_ep(proj)
        sp = _create_sponsorship(s_rep, proj, [ep])
        _approve_sponsorship(s_admin, sp["id"])
        r = s_admin.get(f"{API}/sponsorships/{sp['id']}/proposal.pdf", timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"

    def test_non_owner_403(self, rep, rep2, admin, active_tv_project):
        s_rep, _ = rep
        s_rep2, _ = rep2
        s_admin, _ = admin
        proj = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        ep = _next_free_ep(proj)
        sp = _create_sponsorship(s_rep, proj, [ep])
        _approve_sponsorship(s_admin, sp["id"])
        r = s_rep2.get(f"{API}/sponsorships/{sp['id']}/proposal.pdf", timeout=15)
        assert r.status_code == 403


# ==================== Sponsorship Duplicate w/ Episode Override ====================
class TestSponsorshipDuplicateEpisodeOverride:
    def test_duplicate_with_episode_override(self, rep, admin, active_tv_project):
        s_rep, _ = rep
        s_admin, _ = admin
        proj = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        # Parent uses some episode; then admin requests revision; rep duplicates with new episode number override
        parent_ep = _next_free_ep(proj)
        parent = _create_sponsorship(s_rep, proj, [parent_ep], offer=2000.0)
        _request_revision(s_admin, "sponsorship", parent["id"])
        # Pick different episode
        new_ep = _next_free_ep(proj, exclude={parent_ep})
        r = s_rep.post(f"{API}/sponsorships/{parent['id']}/duplicate",
                       json={"episode_numbers": [new_ep], "offer_amount_usd": 2500.0},
                       timeout=15)
        assert r.status_code in (200, 201), r.text
        new = r.json()
        assert new["status"] == "revised"
        assert new["parent_proposal_id"] == parent["id"]
        assert new["episode_numbers"] == [new_ep]
        assert new["offer_amount_usd"] == 2500.0

    def test_duplicate_conflict_with_other_rep_approved(self, rep, rep2, admin, active_tv_project):
        s_rep, _ = rep
        s_rep2, _ = rep2
        s_admin, _ = admin
        proj = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        # rep2 gets an episode approved
        ep_locked = _next_free_ep(proj)
        sp_r2 = _create_sponsorship(s_rep2, proj, [ep_locked], offer=1800.0)
        _approve_sponsorship(s_admin, sp_r2["id"])
        # rep creates parent on different episode
        proj2 = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        parent_ep = _next_free_ep(proj2)
        parent = _create_sponsorship(s_rep, proj2, [parent_ep])
        _request_revision(s_admin, "sponsorship", parent["id"])
        # Try to duplicate over locked episode
        r = s_rep.post(f"{API}/sponsorships/{parent['id']}/duplicate",
                       json={"episode_numbers": [ep_locked]}, timeout=15)
        assert r.status_code == 409, f"Expected 409 got {r.status_code}: {r.text}"
        assert "already sponsored" in r.text.lower() or "already" in r.text.lower()

    def test_duplicate_empty_episodes(self, rep, admin, active_tv_project):
        s_rep, _ = rep
        s_admin, _ = admin
        proj = s_rep.get(f"{API}/tv-projects/{active_tv_project['id']}", timeout=15).json()
        parent_ep = _next_free_ep(proj)
        parent = _create_sponsorship(s_rep, proj, [parent_ep])
        _request_revision(s_admin, "sponsorship", parent["id"])
        # Empty list — per contract either 400 OR defaults to parent's episodes
        r = s_rep.post(f"{API}/sponsorships/{parent['id']}/duplicate",
                       json={"episode_numbers": []}, timeout=15)
        # Per code path: pick() treats [] as not-None so uses [] → then "if not episodes" → 400
        # Both are acceptable per contract.
        if r.status_code == 400:
            pass  # ok
        else:
            assert r.status_code in (200, 201)
            new = r.json()
            assert new["episode_numbers"] == parent["episode_numbers"]
