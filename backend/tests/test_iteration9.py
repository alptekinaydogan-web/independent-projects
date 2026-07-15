"""Iteration 9 — Auto-email approved proposal PDF via Resend (fire-and-forget).

Verifies:
  - Approving a banner or sponsorship proposal enqueues a background email task
    that writes a `proposal.<kind>.pdf_emailed` (RESEND ok) OR
    `pdf_email_failed` (dev fallback, empty RESEND_API_KEY) audit entry.
  - Audit entry has correct entity_id, details.to (rep email) and pdf_bytes > 5000.
  - /decision endpoint returns quickly (background task detached).
  - PDF used for email path is the rep-facing view (internal notes stripped).
  - Non-approval decisions (revision_requested, rejected) emit NO email audit.
  - Duplicate + approve of revised proposal emits a fresh pdf_email audit entry.
"""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"

ADMIN = {"email": "admin@independentmedia.hub", "password": "Admin2026!"}
REP1 = {"email": "victor.laurent@parismedia.fr", "password": "Rep2026!"}

SECRET = "SECRETXYZ_NOLEAK_" + uuid.uuid4().hex[:6].upper()

EMAIL_ACTIONS = {
    "banner": ("proposal.banner.pdf_emailed", "proposal.banner.pdf_email_failed"),
    "sponsorship": ("proposal.sponsorship.pdf_emailed", "proposal.sponsorship.pdf_email_failed"),
}


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


def _get_inv_item(sess):
    r = sess.get(f"{API}/inventory", timeout=15)
    assert r.status_code == 200
    return r.json()["items"][0]


def _poll_audit(admin_sess, entity_id, expected_actions, timeout=8.0):
    """Poll audit-log looking for the expected action(s) on the entity."""
    end = time.time() + timeout
    last = []
    while time.time() < end:
        r = admin_sess.get(f"{API}/admin/audit-log", params={"limit": 200}, timeout=15)
        assert r.status_code == 200, r.text
        rows = r.json()
        matches = [x for x in rows
                   if x.get("entity_id") == entity_id
                   and x.get("action") in expected_actions]
        if matches:
            return matches[0], rows
        last = rows
        time.sleep(0.4)
    return None, last


def _find_active_tv(sess):
    projects = sess.get(f"{API}/tv-projects", timeout=15).json()
    for p in projects:
        detail = sess.get(f"{API}/tv-projects/{p['id']}", timeout=15).json()
        taken = set()
        for e in detail.get("sponsored_episodes", []) or []:
            taken.add(e.get("episode") if isinstance(e, dict) else e)
        free = detail["total_episodes"] - len(taken)
        if free >= 2:
            return detail
    raise RuntimeError("No TV project with free episodes")


def _next_free(detail, exclude=None):
    exclude = exclude or set()
    taken = set()
    for e in detail.get("sponsored_episodes", []) or []:
        taken.add(e.get("episode") if isinstance(e, dict) else e)
    taken |= exclude
    for e in range(1, detail["total_episodes"] + 1):
        if e not in taken:
            return e
    raise RuntimeError("no free episode")


# =================== Banner ===================
class TestBannerApprovalEmail:
    def test_approval_emits_email_audit_entry_and_is_fast(self, rep, admin):
        s_rep, rep_user = rep
        s_admin, _ = admin
        inv = _get_inv_item(s_rep)
        # Submit a fresh banner proposal
        payload = {
            "proposal_name": f"TEST_it9_banner_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_it9",
            "inventory_id": inv["id"],
            "impressions": 50000,
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "offer_amount_usd": 1500.0,
            "notes": "iteration 9 email test",
        }
        r = s_rep.post(f"{API}/campaigns", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]

        # Approve — measure response time (background must NOT block)
        t0 = time.perf_counter()
        r2 = s_admin.patch(f"{API}/campaigns/{pid}/decision", json={
            "decision": "approved",
            "representative_feedback": "shipped",
            "internal_notes": SECRET,
        }, timeout=15)
        elapsed = time.perf_counter() - t0
        assert r2.status_code == 200, r2.text
        assert elapsed < 3.0, f"/decision took {elapsed:.2f}s — background task blocking?"

        # Poll audit log for email entry (either ok=True or fallback ok=False)
        entry, rows = _poll_audit(s_admin, pid, EMAIL_ACTIONS["banner"])
        assert entry is not None, (
            f"No pdf_email* audit entry for banner {pid} within 8s. "
            f"Recent actions: {[r.get('action') for r in rows[:10]]}"
        )
        assert entry["action"] in EMAIL_ACTIONS["banner"]
        assert entry["entity_id"] == pid
        assert entry["entity_type"] == "campaign"
        details = entry.get("details") or {}
        assert details.get("to") == rep_user["email"], f"to mismatch: {details}"
        assert isinstance(details.get("pdf_bytes"), int) and details["pdf_bytes"] > 5000, (
            f"pdf_bytes suspicious: {details.get('pdf_bytes')}"
        )
        assert "ok" in details

    def test_rep_pdf_does_not_leak_internal_notes(self, rep, admin):
        """The email path builds the PDF from strip_internal_notes(); the rep PDF endpoint
        uses the same helper. Stand-in verification via GET /proposal.pdf."""
        s_rep, _ = rep
        s_admin, _ = admin
        inv = _get_inv_item(s_rep)
        payload = {
            "proposal_name": f"TEST_it9_leak_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_it9",
            "inventory_id": inv["id"],
            "impressions": 10000,
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "offer_amount_usd": 900.0,
        }
        pid = s_rep.post(f"{API}/campaigns", json=payload, timeout=15).json()["id"]
        r = s_admin.patch(f"{API}/campaigns/{pid}/decision", json={
            "decision": "approved",
            "representative_feedback": "ok",
            "internal_notes": SECRET,
        }, timeout=15)
        assert r.status_code == 200
        pdf = s_rep.get(f"{API}/campaigns/{pid}/proposal.pdf", timeout=30)
        assert pdf.status_code == 200
        assert pdf.content[:5] == b"%PDF-"
        assert SECRET.encode() not in pdf.content, "Internal notes leaked into rep PDF"
        assert b"internal_notes" not in pdf.content

    def test_non_approval_decisions_emit_no_email_audit(self, rep, admin):
        s_rep, _ = rep
        s_admin, _ = admin
        inv = _get_inv_item(s_rep)

        # revision_requested
        pid1 = s_rep.post(f"{API}/campaigns", json={
            "proposal_name": f"TEST_it9_rev_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_it9",
            "inventory_id": inv["id"],
            "impressions": 10000,
            "start_date": "2026-03-01",
            "end_date": "2026-03-15",
            "offer_amount_usd": 700.0,
        }, timeout=15).json()["id"]
        s_admin.patch(f"{API}/campaigns/{pid1}/decision", json={
            "decision": "revision_requested", "representative_feedback": "tweak"
        }, timeout=15)

        # rejected
        pid2 = s_rep.post(f"{API}/campaigns", json={
            "proposal_name": f"TEST_it9_rej_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_it9",
            "inventory_id": inv["id"],
            "impressions": 10000,
            "start_date": "2026-03-01",
            "end_date": "2026-03-15",
            "offer_amount_usd": 700.0,
        }, timeout=15).json()["id"]
        s_admin.patch(f"{API}/campaigns/{pid2}/decision", json={
            "decision": "rejected", "representative_feedback": "no"
        }, timeout=15)

        # Give any (incorrectly enqueued) background task a chance to run
        time.sleep(2.5)
        rows = s_admin.get(f"{API}/admin/audit-log",
                            params={"limit": 500}, timeout=15).json()
        for pid in (pid1, pid2):
            offenders = [x for x in rows if x.get("entity_id") == pid
                         and x.get("action") in EMAIL_ACTIONS["banner"]]
            assert not offenders, f"Non-approval decision emitted email audit: {offenders}"


# =================== Sponsorship ===================
class TestSponsorshipApprovalEmail:
    def test_sponsorship_approval_emits_email_audit(self, rep, admin):
        s_rep, rep_user = rep
        s_admin, _ = admin
        proj = _find_active_tv(s_rep)
        ep = _next_free(proj)
        payload = {
            "proposal_name": f"TEST_it9_tv_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_it9",
            "tv_project_id": proj["id"],
            "episode_numbers": [ep],
            "offer_amount_usd": 3000.0,
            "notes": "iteration 9 sponsorship email test",
        }
        pid = s_rep.post(f"{API}/sponsorships", json=payload, timeout=15).json()["id"]

        t0 = time.perf_counter()
        r = s_admin.patch(f"{API}/sponsorships/{pid}/decision", json={
            "decision": "approved",
            "representative_feedback": "great",
            "internal_notes": SECRET,
        }, timeout=15)
        elapsed = time.perf_counter() - t0
        assert r.status_code == 200, r.text
        assert elapsed < 3.0, f"/decision took {elapsed:.2f}s — background blocking?"

        entry, rows = _poll_audit(s_admin, pid, EMAIL_ACTIONS["sponsorship"])
        assert entry is not None, (
            f"No sponsorship pdf_email* audit for {pid}. "
            f"Recent: {[r.get('action') for r in rows[:10]]}"
        )
        assert entry["entity_id"] == pid
        assert entry["entity_type"] == "sponsorship"
        details = entry.get("details") or {}
        assert details.get("to") == rep_user["email"]
        assert isinstance(details.get("pdf_bytes"), int) and details["pdf_bytes"] > 5000

    def test_sponsorship_non_approval_no_email(self, rep, admin):
        s_rep, _ = rep
        s_admin, _ = admin
        proj = _find_active_tv(s_rep)
        ep = _next_free(proj)
        pid = s_rep.post(f"{API}/sponsorships", json={
            "proposal_name": f"TEST_it9_tv_rev_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_it9",
            "tv_project_id": proj["id"],
            "episode_numbers": [ep],
            "offer_amount_usd": 2000.0,
        }, timeout=15).json()["id"]
        s_admin.patch(f"{API}/sponsorships/{pid}/decision", json={
            "decision": "revision_requested", "representative_feedback": "tweak"
        }, timeout=15)
        time.sleep(2.0)
        rows = s_admin.get(f"{API}/admin/audit-log",
                            params={"limit": 300}, timeout=15).json()
        offenders = [x for x in rows if x.get("entity_id") == pid
                     and x.get("action") in EMAIL_ACTIONS["sponsorship"]]
        assert not offenders, f"Non-approval sponsorship decision emitted email audit: {offenders}"


# =================== Regression: duplicate + approve ===================
class TestDuplicateApprovalEmail:
    def test_revised_banner_approval_emits_new_audit_entry(self, rep, admin):
        s_rep, rep_user = rep
        s_admin, _ = admin
        inv = _get_inv_item(s_rep)

        # Parent → revision requested
        parent_id = s_rep.post(f"{API}/campaigns", json={
            "proposal_name": f"TEST_it9_parent_{uuid.uuid4().hex[:6]}",
            "client_reference": "TEST_it9",
            "inventory_id": inv["id"],
            "impressions": 10000,
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "offer_amount_usd": 800.0,
        }, timeout=15).json()["id"]
        s_admin.patch(f"{API}/campaigns/{parent_id}/decision", json={
            "decision": "revision_requested", "representative_feedback": "tweak it"
        }, timeout=15)

        # Duplicate → new revised proposal
        dup = s_rep.post(f"{API}/campaigns/{parent_id}/duplicate",
                          json={"offer_amount_usd": 1100.0}, timeout=15)
        assert dup.status_code in (200, 201), dup.text
        new_id = dup.json()["id"]
        assert new_id != parent_id

        # Approve the revised one
        r = s_admin.patch(f"{API}/campaigns/{new_id}/decision", json={
            "decision": "approved", "representative_feedback": "ok now"
        }, timeout=15)
        assert r.status_code == 200

        entry, rows = _poll_audit(s_admin, new_id, EMAIL_ACTIONS["banner"])
        assert entry is not None, (
            f"No pdf_email* audit for revised banner {new_id}. "
            f"Recent: {[r.get('action') for r in rows[:10]]}"
        )
        assert entry["entity_id"] == new_id
        details = entry.get("details") or {}
        assert details.get("to") == rep_user["email"]
        assert details.get("pdf_bytes", 0) > 5000
