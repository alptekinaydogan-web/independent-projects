# CI Pipeline

Production-grade build-and-dependency quality gate for **Independent Projects**.
No code may be deployed to production unless every required CI job is green on the exact commit being deployed.

---

## 1. Purpose

The CI pipeline exists to guarantee that the project **installs and builds successfully from a clean checkout** on every push and pull request targeting `main`. It intentionally does not deploy — deployment is a separate, gated action.

Concretely, CI verifies:

- All frontend dependencies resolve deterministically from the authoritative lockfile.
- The frontend production build succeeds and emits the expected artifacts.
- All backend dependencies resolve into a fresh virtual environment.
- `pip check` reports no broken or incompatible requirements.
- The FastAPI application imports cleanly.

Any failure blocks the pull request from merging.

---

## 2. Repository Structure

```
/
├── frontend/           # React (CRA + CRACO), Yarn Classic
│   ├── package.json
│   ├── yarn.lock        # authoritative lockfile
│   └── ...
├── backend/            # FastAPI, Python 3.11
│   ├── requirements.txt
│   ├── server.py
│   └── ...
├── .github/
│   ├── workflows/ci.yml
│   └── dependabot.yml
└── docs/CI_PIPELINE.md  # this document
```

The workflow paths (`frontend/`, `backend/`) match this monorepo structure.

---

## 3. Runtime Versions

| Component | Version              | Enforced in         |
|-----------|----------------------|---------------------|
| Node.js   | 20 (LTS)             | `ci.yml` frontend job |
| Yarn      | 1.22.x (Yarn Classic) | `packageManager` in `frontend/package.json` |
| Python    | 3.11                 | `ci.yml` backend job |

---

## 4. Frontend Package Manager Policy

**Yarn Classic 1.22.x is authoritative** for this repository.

Reasons:

1. `frontend/package.json` uses a substantial [`resolutions`](https://classic.yarnpkg.com/lang/en/docs/selective-version-resolutions/) block for pinned security overrides. Resolutions are a Yarn-only feature; migrating them to npm would require re-authoring them as `overrides` and validating every one.
2. The `packageManager` field in `frontend/package.json` pins Yarn Classic with its checksum.
3. The development / preview runtime already depends on Yarn (`yarn start`, hot reload, supervisor process).

**Policy consequences:**

- Only **one** lockfile — `frontend/yarn.lock` — is committed. `package-lock.json` **must not** be added. CI fails the build if it is detected.
- All local development uses `yarn install` (never `npm install`).
- CI installs with `yarn install --frozen-lockfile --non-interactive`. This is the deterministic clean-install equivalent of `npm ci`.
- `yarn install --frozen-lockfile` fails immediately if `package.json` and `yarn.lock` are out of sync, exactly the guarantee we want in CI.

### Why deterministic clean installation is required

`yarn install` (without `--frozen-lockfile`) will silently update the lockfile if it disagrees with `package.json`. In CI that produces flaky builds and hides genuine dependency drift. `--frozen-lockfile` never mutates the lockfile — if it can't satisfy the request, it exits non-zero, forcing the developer to regenerate the lockfile locally and commit it.

### Why `npm ci` when npm is authoritative

`npm ci`:
- Reads only from `package-lock.json`.
- Wipes `node_modules` first for a truly clean install.
- Never modifies the lockfile.

Our Yarn-authoritative equivalent is `yarn install --frozen-lockfile --non-interactive`. It provides the same three guarantees. `--force` and `--legacy-peer-deps` are **prohibited** across the entire pipeline because they hide unresolved dependency conflicts instead of fixing them.

---

## 5. What CI Validates

### Frontend job (`frontend`)

1. Checks out the repository.
2. Sets up Node.js 20 with Yarn dependency cache keyed on `frontend/yarn.lock`.
3. Fails immediately if `package-lock.json` is committed.
4. Runs `yarn install --frozen-lockfile --non-interactive` scoped to `frontend/`.
5. Runs `yarn build` (CRACO production build).
6. Verifies `frontend/build/index.html`, `frontend/build/static/` exist.

### Backend job (`backend`)

1. Checks out the repository.
2. Sets up Python 3.11 with pip dependency cache keyed on `backend/requirements.txt`.
3. Creates `.venv/` and upgrades pip.
4. Installs `-r requirements.txt` — no `--force`, no ignore flags.
5. Runs `pip check` to detect broken / conflicting requirements.
6. Imports the FastAPI application to catch runtime import errors.

Every step runs under `set -euo pipefail` — any failure fails the job.

---

## 6. Safety Controls

- **Concurrency:** duplicate runs on the same branch or PR are cancelled (`cancel-in-progress: true`).
- **Least-privilege:** the workflow's default `GITHUB_TOKEN` is `read-only`.
- **Explicit working directories:** each job runs inside its component directory.
- **Cache keys:** based on the real lockfiles (`frontend/yarn.lock`, `backend/requirements.txt`).
- **Build output verification:** the frontend job asserts artifacts exist before marking success.

No deployment steps are present. This workflow is a **build and dependency quality gate only**.

---

## 7. Resolving a Dependency Failure

### Frontend

Symptom: `yarn install --frozen-lockfile` fails with "Your lockfile needs to be updated".

Cause: `package.json` and `yarn.lock` are out of sync.

Fix:
```bash
cd frontend
yarn install                       # regenerate the lockfile
yarn install --frozen-lockfile     # verify determinism
yarn build                         # verify production build
git add package.json yarn.lock
git commit -m "chore(deps): sync frontend lockfile"
```

Symptom: `ERESOLVE` / peer-dependency conflict at install time.

**Do not** work around it with `--force` or `--legacy-peer-deps`. Investigate:

1. Find the conflicting peer with `yarn why <package>`.
2. Upgrade the offending package to a version that declares the correct peer range.
3. If the upstream package hasn't updated yet and the actual runtime behaviour is compatible, add a targeted entry to the `resolutions` block **and** document the reason inline in a comment.

Symptom: transitive vulnerability alert.

Add a targeted `resolutions` entry pinning the vulnerable transitive dep to a fixed version. Verify with `yarn install --frozen-lockfile && yarn build`, then commit `package.json` + `yarn.lock`.

### Backend

Symptom: `pip install` fails with a resolver conflict.

Fix:
1. Read the resolver output — it always identifies both conflicting requesters.
2. Update whichever pinned version is behind, or remove a redundant explicit pin if the package is also a transitive dependency of another declared package.
3. Re-run `pip install -r requirements.txt && pip check` locally in a clean venv.
4. Commit the updated `requirements.txt`.

Symptom: `pip check` reports an incompatibility.

Update the affected pin. Never suppress `pip check`.

---

## 8. Updating Dependencies

### Frontend

```bash
cd frontend
yarn upgrade-interactive --latest      # interactive picker for updates
yarn install --frozen-lockfile         # verify determinism
yarn build                             # verify production build
```

For a single package: `yarn upgrade <name>@<version>`.

Always commit `package.json` + `yarn.lock` together.

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install --upgrade <package>
pip freeze | sort > requirements.txt   # regenerate pins
pip check                              # verify
```

Never edit `requirements.txt` by hand for anything other than removing a redundant entry or swapping a URL. All version pins should come from `pip freeze` in a clean venv.

---

## 9. Lockfile Policy

- One authoritative lockfile per component: `frontend/yarn.lock`, `backend/requirements.txt`.
- The frontend lockfile must always be produced by `yarn install`. Never hand-edit.
- CI fails the build if `frontend/package-lock.json` is committed.
- `frontend/yarn.lock` and `backend/requirements.txt` must be committed on every dependency change.

---

## 10. Dependabot Policy

Dependabot (`.github/dependabot.yml`) opens weekly pull requests for:

- `npm` ecosystem (reads `frontend/package.json` + `frontend/yarn.lock`).
- `pip` ecosystem (reads `backend/requirements.txt`).
- `github-actions` (workflow versions).

Rules:

- Minor and patch updates are **grouped** to keep PR noise low.
- Major updates are opened as **separate** PRs and must be reviewed by a human.
- `react` / `react-dom` / `react-scripts` (frontend) and `pydantic` / `fastapi` (backend) major upgrades are ignored — these are coordinated by hand due to breaking-change surface.
- `litellm` and `emergentintegrations` are ignored because they are served from a private CDN that Dependabot cannot resolve.
- **Auto-merge is disabled.** Every PR must pass CI and be reviewed before merging.

---

## 11. Production Deployment Rule

> **No code may be deployed to production unless all required CI jobs are green on the exact commit being deployed.**

This rule applies to every environment target (Emergent preview, Vercel, Railway, or self-hosted). Green CI on `main` is the only artifact of trust in the deployment pipeline.
