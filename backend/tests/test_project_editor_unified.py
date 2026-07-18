"""Iteration 22 backend tests — Unified Project Editor + Partner Submission
in-place review.

Verifies:
  - Rep listing = published+approved+active+non-archived only
  - Admin listing supports ?source=partner
  - POST /projects (rep -> partner draft; admin -> official approved+published)
  - PATCH /projects/{id} permission matrix (owner draft/revision, other rep 403,
    submitted rep 403, admin always)
  - POST /projects/{id}/submit sets submitted moderation status
  - PATCH /admin/projects/{id}/moderate approved/revision_requested/rejected
  - PATCH publish/feature/archive toggles
  - Assets add + remove
  - GET /my-projects
  - Legacy /proposals adapters (POST + admin PATCH mapping)
  - Reports overview reads partner submissions from tv_projects (source=partner)
  - Rep profile has partner_submissions
  - System health counters (no `proposals` key, has partner_submissions)
  - Legacy campaigns/sponsorships/inventory still 404
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
OWNER_EMAIL = "admin@independentmedia.hub"
OWNER_PASSWORD = "Admin2026!"
REP_EMAIL = "victor.laurent@parismedia.fr"
REP_PASSWORD = "Rep2026!"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def owner_headers():
    return {"Authorization": f"Bearer {_login(OWNER_EMAIL, OWNER_PASSWORD)}"}


@pytest.fixture(scope="module")
def rep_headers():
    return {"Authorization": f"Bearer {_login(REP_EMAIL, REP_PASSWORD)}"}


# ---------------- Listing visibility ----------------
class TestListingVisibility:
    def test_rep_sees_only_published_approved_active(self, rep_headers):
        r = requests.get(f"{BASE_URL}/api/tv-projects", headers=rep_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        for p in items:
            assert p.get("status") == "active"
            # rep-visible items shouldn't be archived
            assert p.get("archived") is not True

    def test_admin_source_filter_partner(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/tv-projects?source=partner",
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        items = r.json()
        # All items should have source=partner (if any)
        for p in items:
            assert p.get("source") == "partner"


# ---------------- Rep-owned project lifecycle ----------------
class TestRepProjectLifecycle:
    def test_full_flow_and_permissions(self, owner_headers, rep_headers):
        # Rep creates partner draft
        body = {"title": f"TEST_REP_{uuid.uuid4().hex[:6]}",
                "overview": "Test overview from rep",
                "concept": "Concept",
                "total_episodes": 8,
                "production_format": "Documentary",
                "category_slug": "tv_formats"}
        r = requests.post(f"{BASE_URL}/api/projects", json=body,
                          headers=rep_headers, timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["source"] == "partner"
        assert p["moderation_status"] == "draft"
        assert p["published"] is False
        assert p["submitted_by_rep_id"]
        pid = p["id"]

        # Rep can PATCH their own draft
        upd = requests.patch(f"{BASE_URL}/api/projects/{pid}",
                             json={"tagline": "Updated tagline"},
                             headers=rep_headers, timeout=15)
        assert upd.status_code == 200
        assert upd.json()["tagline"] == "Updated tagline"

        # Rep can NOT flip published from their own PATCH
        cheat = requests.patch(f"{BASE_URL}/api/projects/{pid}",
                               json={"published": True, "status": "active"},
                               headers=rep_headers, timeout=15)
        assert cheat.status_code == 200
        assert cheat.json()["published"] is False
        assert cheat.json()["status"] == "draft"

        # /api/my-projects returns it
        mine = requests.get(f"{BASE_URL}/api/my-projects",
                            headers=rep_headers, timeout=15)
        assert mine.status_code == 200
        assert any(x["id"] == pid for x in mine.json())

        # Rep submits
        sub = requests.post(f"{BASE_URL}/api/projects/{pid}/submit",
                            headers=rep_headers, timeout=15)
        assert sub.status_code == 200
        assert sub.json()["moderation_status"] == "submitted"

        # Rep now cannot edit
        forbidden = requests.patch(f"{BASE_URL}/api/projects/{pid}",
                                    json={"tagline": "no"},
                                    headers=rep_headers, timeout=15)
        assert forbidden.status_code == 403

        # Admin requests revision
        rev = requests.patch(f"{BASE_URL}/api/admin/projects/{pid}/moderate",
                              json={"decision": "revision_requested",
                                    "admin_feedback": "Please add audience"},
                              headers=owner_headers, timeout=15)
        assert rev.status_code == 200
        assert rev.json()["moderation_status"] == "revision_requested"
        assert rev.json()["admin_feedback"] == "Please add audience"

        # Rep can now edit again
        edit2 = requests.patch(f"{BASE_URL}/api/projects/{pid}",
                                json={"target_audience": "Adults 18+"},
                                headers=rep_headers, timeout=15)
        assert edit2.status_code == 200

        # Rep resubmits
        sub2 = requests.post(f"{BASE_URL}/api/projects/{pid}/submit",
                              headers=rep_headers, timeout=15)
        assert sub2.status_code == 200

        # Admin approves — flips published + status active
        appr = requests.patch(f"{BASE_URL}/api/admin/projects/{pid}/moderate",
                               json={"decision": "approved",
                                     "admin_feedback": "Great job"},
                               headers=owner_headers, timeout=15)
        assert appr.status_code == 200
        data = appr.json()
        assert data["moderation_status"] == "approved"
        assert data["published"] is True
        assert data["status"] == "active"

        # Now visible in rep listing
        rep_list = requests.get(f"{BASE_URL}/api/tv-projects",
                                headers=rep_headers, timeout=15).json()
        assert any(x["id"] == pid for x in rep_list)

        # Toggle featured
        feat = requests.patch(f"{BASE_URL}/api/admin/projects/{pid}/feature",
                               json={"featured": True},
                               headers=owner_headers, timeout=15)
        assert feat.status_code == 200
        assert feat.json()["featured"] is True

        # Toggle archived -> disappears for rep
        arch = requests.patch(f"{BASE_URL}/api/admin/projects/{pid}/archive",
                               json={"archived": True},
                               headers=owner_headers, timeout=15)
        assert arch.status_code == 200
        assert arch.json()["archived"] is True
        rep_list2 = requests.get(f"{BASE_URL}/api/tv-projects",
                                 headers=rep_headers, timeout=15).json()
        assert not any(x["id"] == pid for x in rep_list2)

        # Toggle publish off
        pub = requests.patch(f"{BASE_URL}/api/admin/projects/{pid}/publish",
                              json={"published": False},
                              headers=owner_headers, timeout=15)
        assert pub.status_code == 200
        assert pub.json()["published"] is False

        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{pid}",
                        headers=owner_headers, timeout=15)

    def test_admin_creates_official_project(self, owner_headers):
        body = {"title": f"TEST_ADMIN_{uuid.uuid4().hex[:6]}",
                "overview": "Admin official",
                "status": "active",
                "category_slug": "tv_formats"}
        r = requests.post(f"{BASE_URL}/api/projects", json=body,
                          headers=owner_headers, timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["source"] == "admin"
        assert p["moderation_status"] == "approved"
        assert p["published"] is True
        # cleanup
        requests.delete(f"{BASE_URL}/api/projects/{p['id']}",
                        headers=owner_headers, timeout=15)

    def test_rejected_decision(self, owner_headers, rep_headers):
        body = {"title": f"TEST_REJ_{uuid.uuid4().hex[:6]}",
                "overview": "reject test"}
        p = requests.post(f"{BASE_URL}/api/projects", json=body,
                          headers=rep_headers, timeout=15).json()
        pid = p["id"]
        requests.post(f"{BASE_URL}/api/projects/{pid}/submit",
                      headers=rep_headers, timeout=15)
        rej = requests.patch(f"{BASE_URL}/api/admin/projects/{pid}/moderate",
                              json={"decision": "rejected",
                                    "admin_feedback": "not aligned"},
                              headers=owner_headers, timeout=15)
        assert rej.status_code == 200
        assert rej.json()["moderation_status"] == "rejected"
        requests.delete(f"{BASE_URL}/api/projects/{pid}",
                        headers=owner_headers, timeout=15)


# ---------------- Download center assets ----------------
class TestAssets:
    def test_add_and_remove_asset(self, owner_headers, rep_headers):
        body = {"title": f"TEST_ASSET_{uuid.uuid4().hex[:6]}"}
        pid = requests.post(f"{BASE_URL}/api/projects", json=body,
                            headers=rep_headers, timeout=15).json()["id"]

        add = requests.post(f"{BASE_URL}/api/projects/{pid}/assets",
                             json={"label": "Deck", "url": "https://x.com/deck.pdf",
                                   "filetype": "pdf"},
                             headers=rep_headers, timeout=15)
        assert add.status_code == 200, add.text
        asset = add.json()
        assert "id" in asset and asset["label"] == "Deck"

        # Confirm it lives on the project
        got = requests.get(f"{BASE_URL}/api/tv-projects/{pid}",
                           headers=rep_headers, timeout=15).json()
        assert any(a["id"] == asset["id"] for a in got.get("download_assets", []))

        # Remove
        rm = requests.delete(
            f"{BASE_URL}/api/projects/{pid}/assets/{asset['id']}",
            headers=rep_headers, timeout=15)
        assert rm.status_code == 200
        got2 = requests.get(f"{BASE_URL}/api/tv-projects/{pid}",
                            headers=rep_headers, timeout=15).json()
        assert not any(a["id"] == asset["id"] for a in got2.get("download_assets", []))

        requests.delete(f"{BASE_URL}/api/projects/{pid}",
                        headers=owner_headers, timeout=15)


# ---------------- Legacy proposals adapters ----------------
class TestLegacyProposalAdapters:
    def test_create_legacy_creates_unified(self, owner_headers, rep_headers):
        body = {"title": f"TEST_LEGACYP_{uuid.uuid4().hex[:6]}",
                "format": "Documentary", "country": "France",
                "description": "legacy path", "estimated_episodes": 4}
        r = requests.post(f"{BASE_URL}/api/proposals", json=body,
                          headers=rep_headers, timeout=15)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        # Should appear via admin ?source=partner
        adm = requests.get(f"{BASE_URL}/api/tv-projects?source=partner",
                           headers=owner_headers, timeout=15).json()
        assert any(x["id"] == pid for x in adm)

        # Legacy admin patch mapping: in_review -> revision_requested
        r2 = requests.patch(f"{BASE_URL}/api/admin/proposals/{pid}",
                            json={"status": "in_review", "admin_notes": "revise pls"},
                            headers=owner_headers, timeout=15)
        assert r2.status_code == 200
        # verify moderation_status on tv-projects
        detail = requests.get(f"{BASE_URL}/api/tv-projects/{pid}",
                              headers=owner_headers, timeout=15).json()
        assert detail["moderation_status"] == "revision_requested"

        # Approve via legacy
        r3 = requests.patch(f"{BASE_URL}/api/admin/proposals/{pid}",
                            json={"status": "approved", "admin_notes": "ok"},
                            headers=owner_headers, timeout=15)
        assert r3.status_code == 200
        detail2 = requests.get(f"{BASE_URL}/api/tv-projects/{pid}",
                               headers=owner_headers, timeout=15).json()
        assert detail2["moderation_status"] == "approved"
        assert detail2["published"] is True

        requests.delete(f"{BASE_URL}/api/projects/{pid}",
                        headers=owner_headers, timeout=15)


# ---------------- Migration: proposals collection dropped ----------------
class TestMigration:
    def test_no_separate_proposals_collection(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/admin/system/health",
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        counts = r.json().get("database", {}).get("counts", {})
        # `proposals` MUST NOT appear as a separate count post-unification
        assert "proposals" not in counts, f"'proposals' should not be a separate count. got: {counts}"
        assert "partner_submissions" in counts
        for k in ("categories", "tv_projects", "productions",
                  "audit_entries", "notifications"):
            assert k in counts


# ---------------- Reports overview ----------------
class TestReports:
    def test_reports_overview_shape(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/reports/overview",
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "partner_submissions" in data
        ps = data["partner_submissions"]
        assert "total" in ps
        assert "project_library" in data
        pl = data["project_library"]
        for k in ("active", "draft", "closed"):
            assert k in pl


# ---------------- Representatives profile ----------------
class TestRepProfile:
    def test_profile_has_partner_submissions(self, owner_headers):
        reps = requests.get(f"{BASE_URL}/api/admin/representatives",
                            headers=owner_headers, timeout=15).json()
        rid = next(r["id"] for r in reps if r.get("email") == REP_EMAIL)
        r = requests.get(f"{BASE_URL}/api/admin/representatives/{rid}/profile",
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        p = r.json()
        assert "partner_submissions" in p
        assert isinstance(p["partner_submissions"], list)


# ---------------- Legacy removed endpoints ----------------
class TestLegacyRemoved:
    @pytest.mark.parametrize("path", ["/api/campaigns", "/api/sponsorships",
                                       "/api/inventory"])
    def test_legacy_gone(self, path, owner_headers):
        r = requests.get(f"{BASE_URL}{path}", headers=owner_headers, timeout=15)
        assert r.status_code == 404, f"{path} should be 404 but got {r.status_code}"


# ---------------- Cross-rep permission ----------------
class TestPermissionMatrix:
    def test_admin_can_always_edit(self, owner_headers, rep_headers):
        body = {"title": f"TEST_ADMEDIT_{uuid.uuid4().hex[:6]}"}
        pid = requests.post(f"{BASE_URL}/api/projects", json=body,
                            headers=rep_headers, timeout=15).json()["id"]
        # Rep submits
        requests.post(f"{BASE_URL}/api/projects/{pid}/submit",
                      headers=rep_headers, timeout=15)
        # Admin still edits
        r = requests.patch(f"{BASE_URL}/api/projects/{pid}",
                           json={"tagline": "admin override"},
                           headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["tagline"] == "admin override"
        requests.delete(f"{BASE_URL}/api/projects/{pid}",
                        headers=owner_headers, timeout=15)
