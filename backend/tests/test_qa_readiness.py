"""QA Readiness sweep — post-reseed. Does NOT reseed (fixtures already primed)."""
import os, requests, pytest, time
from pathlib import Path

def _base():
    env = Path("/app/frontend/.env")
    for line in env.read_text().splitlines():
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
    return s, r


@pytest.fixture(scope="module")
def owner():
    s, r = _login(OWNER)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def rep():
    s, r = _login(REP)
    assert r.status_code == 200, r.text
    return s


# ---- OWNER: every admin-page-backing endpoint returns 200 ----
OWNER_ENDPOINTS = [
    "/admin/system/health",
    "/campaigns?include_archived=true",   # /admin/proposals-review data
    "/sponsorships?include_archived=true",
    "/reports/overview",                  # /admin/reports
    "/admin/audit-log?limit=500",
    "/tv-projects",
    "/inventory",
    "/admin/representatives",
    "/notifications",
    "/proposals",                          # editorial concepts
]


@pytest.mark.parametrize("path", OWNER_ENDPOINTS)
def test_owner_page_endpoints(owner, path):
    r = owner.get(f"{API}{path}", timeout=20)
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"


# ---- REP: every rep-page-backing endpoint returns 200 ----
REP_ENDPOINTS = [
    "/campaigns?include_archived=true",   # /rep/banners
    "/sponsorships?include_archived=true",# /rep/sponsorships
    "/tv-projects",                        # /rep/tv catalog
    "/inventory",                          # /rep/banners/new (CampaignBuilder)
    "/reports/overview",                   # /rep/reports (rep-scoped)
    "/notifications",
]


@pytest.mark.parametrize("path", REP_ENDPOINTS)
def test_rep_page_endpoints(rep, path):
    r = rep.get(f"{API}{path}", timeout=20)
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text[:200]}"


def test_rep_tv_project_detail(rep):
    lst = rep.get(f"{API}/tv-projects", timeout=15).json()
    assert isinstance(lst, list) and len(lst) >= 3, lst
    pid = lst[0].get("id") or lst[0].get("_id")
    r = rep.get(f"{API}/tv-projects/{pid}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    # Detail should carry synopsis + episodes
    assert d.get("synopsis") is not None
    assert isinstance(d.get("episodes", []), list)


# ---- PERMISSION GATES ----
def test_rep_cannot_seed(rep):
    r = rep.post(f"{API}/admin/demo/seed", timeout=20)
    assert r.status_code == 403, r.status_code


def test_rep_cannot_access_admin_audit(rep):
    r = rep.get(f"{API}/admin/audit-log", timeout=15)
    assert r.status_code in (401, 403), r.status_code


def test_rep_cannot_access_admin_representatives(rep):
    r = rep.get(f"{API}/admin/representatives", timeout=15)
    assert r.status_code in (401, 403), r.status_code


# ---- REP PRIVACY: internal_notes stripped everywhere ----
def _leak(obj):
    if isinstance(obj, dict):
        v = obj.get("internal_notes")
        if isinstance(v, str) and v.strip():
            return True
        return any(_leak(x) for x in obj.values())
    if isinstance(obj, list):
        return any(_leak(x) for x in obj)
    return False


def test_rep_campaigns_no_internal_notes(rep):
    items = rep.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
    assert len(items) > 0
    assert not _leak(items)


def test_rep_sponsorships_no_internal_notes(rep):
    items = rep.get(f"{API}/sponsorships?include_archived=true", timeout=15).json()
    assert len(items) > 0
    assert not _leak(items)


# ---- STATUS/TERMINOLOGY consistency: only expected labels present ----
ALLOWED_STATUSES = {"pending_review", "revised", "revision_requested",
                    "approved", "rejected", "archived"}


def test_no_stray_status_labels_owner(owner):
    for path in ["/campaigns?include_archived=true", "/sponsorships?include_archived=true"]:
        items = owner.get(f"{API}{path}", timeout=15).json()
        for it in items:
            st = it.get("status")
            # archived is tracked via is_archived; status itself must be in allowed set
            assert st in ALLOWED_STATUSES, f"{path}: unexpected status {st!r}"


# ---- BUSINESS LOGIC: approve a Pending banner with feedback + internal_notes ----
def test_approve_pending_banner_records_and_privacy(owner, rep):
    items = owner.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
    pending = [i for i in items if i.get("status") == "pending_review" and not i.get("is_archived")]
    assert pending, "no pending_review banner available to approve"
    target = pending[0]
    pid = target["id"]

    body = {
        "decision": "approved",
        "representative_feedback": "QA test — approved with feedback",
        "internal_notes": "QA-INTERNAL-SECRET-DO-NOT-LEAK",
    }
    r = owner.patch(f"{API}/campaigns/{pid}/decision", json=body, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("status") == "approved"
    # Owner should still see internal_notes on their view
    assert "QA-INTERNAL-SECRET" in (d.get("internal_notes") or "")

    # Audit should now have a banner.approved entry for this proposal
    audit = owner.get(f"{API}/admin/audit-log?limit=500", timeout=15).json()
    audit_items = audit if isinstance(audit, list) else audit.get("items", [])
    matches = [a for a in audit_items
               if a.get("action") == "proposal.banner.approved" and a.get("entity_id") == pid]
    assert matches, "no audit entry for banner.approved"

    # Rep-side view of the same proposal must NOT contain the internal note
    time.sleep(0.5)
    rep_items = rep.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
    rep_view = next((c for c in rep_items if c.get("id") == pid), None)
    assert rep_view is not None
    assert rep_view.get("representative_feedback") == "QA test — approved with feedback"
    # No leak anywhere in the payload
    payload_text = str(rep_view)
    assert "QA-INTERNAL-SECRET" not in payload_text
    assert not _leak(rep_view)


# ---- EDGE CASE: rep Duplicate & revise on a revision_requested banner ----
def test_rep_duplicate_revision_requested_banner(rep):
    items = rep.get(f"{API}/campaigns?include_archived=true", timeout=15).json()
    src = next((c for c in items if c.get("status") == "revision_requested"), None)
    assert src is not None, "no revision_requested banner for duplicate test"
    src_id = src["id"]
    body = {
        "campaign_name": (src.get("campaign_name") or "Campaign") + " (QA revised)",
        "offer_details": "Revised offer — QA test",
        "notes": "QA duplicate & revise smoke",
    }
    r = rep.post(f"{API}/campaigns/{src_id}/duplicate", json=body, timeout=30)
    assert r.status_code in (200, 201), r.text
    d = r.json()
    assert d.get("status") == "revised", d.get("status")
    assert d.get("parent_proposal_id") == src_id or d.get("revision_of") == src_id, d


# ---- PERFORMANCE smoke: initial content endpoints under 3s ----
PERF_PATHS = [
    "/campaigns?include_archived=true",
    "/reports/overview",
    "/admin/audit-log?limit=200",
]


@pytest.mark.parametrize("path", PERF_PATHS)
def test_perf_under_3s(owner, path):
    t = time.perf_counter()
    r = owner.get(f"{API}{path}", timeout=10)
    elapsed = time.perf_counter() - t
    assert r.status_code == 200
    assert elapsed < 3.0, f"{path} took {elapsed:.2f}s"


# ---- CSV export smoke ----
def test_reports_csv_export(owner):
    r = owner.get(f"{API}/reports/proposals/export.csv?month=2026-01", timeout=20)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "").lower() or r.text
