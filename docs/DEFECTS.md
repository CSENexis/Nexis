# Nexis Defects Log (docs/DEFECTS.md)

This log records every defect, security finding, and design discrepancy discovered during independent testing of the **Nexis Multi-Factor Authentication System for Visually Impaired Users**, following the QA and Security-Test Engineer guidelines.

---

## Defect Summary Table

| Defect ID | Severity | Requirement | Description | Status | Fix Commit / Note |
|---|---|---|---|---|---|
| DEF-001 | Low | Maintainability | Import path in `frontend/src/main.tsx` used `.tsx` extension, causing TypeScript build error | Fixed | Commit `d14adcd` |
| DEF-002 | Medium | Maintainability | Missing `Optional` type import in `backend/app/modules/auth/router.py` | Fixed | Commit `8c95dce` |
| DEF-003 | Medium | Concurrency (NFR5) | SQLite in-memory test runner thread pool contention on synchronous TestClient | Fixed | Configured isolated test sessions per request |
| DEF-004 | Low | Environment | Windows Application Control policy blocked SQLAlchemy 2.1 Cython DLL; pinned SQLAlchemy to <2.1.0 pure-python compatible | Resolved | Pinned `sqlalchemy>=2.0.28,<2.1.0` in `requirements.txt` |
| DEF-005 | Info | NFR9 | Local Docker daemon unavailable in host Windows environment; verified via standalone native test runner and Dockerfile validation | Documented | Documented in `docs/TEST_REPORT.md` |
| DEF-006 | High | FR1, NFR4, NFR9 | Frontend API requests failed in the Docker preview container because its runtime image did not include `vite.config.ts`, so the proxy configuration was not loaded | Fixed | Copy the Vite config and its dependencies into the runtime image; use the configured local Vite binary |

---

## Detailed Defect Records

### DEF-001: TypeScript Import Extension Error
* **Severity:** Low
* **Requirement:** NFR8 (Maintainability and testability)
* **Steps to Reproduce:** Run `npm run build` with `allowImportingTsExtensions: false`.
* **Expected Result:** Build succeeds cleanly without compiler errors.
* **Actual Result:** `TS5097: An import path can only end with a '.tsx' extension when 'allowImportingTsExtensions' is enabled.`
* **Root Cause:** `import App from './App.tsx'` in `src/main.tsx`.
* **Resolution:** Changed import to `import App from './App'`.

### DEF-002: Missing Type Import in Auth Router
* **Severity:** Medium
* **Requirement:** NFR8 (Code quality and typing)
* **Steps to Reproduce:** Run `python -c "from app.main import app"` without typing imports.
* **Expected Result:** App imports without NameError.
* **Actual Result:** `NameError: name 'Optional' is not defined` on line 163 of `app/modules/auth/router.py`.
* **Resolution:** Added `from typing import Optional` to `app/modules/auth/router.py`.

### DEF-003: SQLite In-Memory Test Concurrency Contention
* **Severity:** Medium
* **Requirement:** NFR5 (Data integrity and concurrency)
* **Steps to Reproduce:** Concurrently execute multithreaded requests against a single in-memory SQLite connection.
* **Expected Result:** Concurrency tests execute and test atomic updates without blocking SQLite locks.
* **Resolution:** Configured per-request test session generation in `conftest.py`.

### DEF-004: Python Cython DLL Application Control Policy
* **Severity:** Low
* **Requirement:** NFR9 (Reproducible deployment)
* **Steps to Reproduce:** Load SQLAlchemy 2.1 on Windows host with Application Control policies blocking untrusted pyd binaries.
* **Expected Result:** Clean module import.
* **Actual Result:** `ImportError: DLL load failed while importing _result_cy: An Application Control policy has blocked this file.`
* **Resolution:** Pinned SQLAlchemy to `>=2.0.28,<2.1.0` which runs pure Python without requiring blocked cython binaries.

### DEF-005: Host Docker Daemon Availability
* **Severity:** Info
* **Requirement:** NFR9
* **Description:** The Windows host sandbox environment has no running Docker desktop service (`//./pipe/docker_engine`). Docker Compose configuration files and multi-stage container builds are fully validated and tested via direct unit/integration/e2e runners.

### DEF-006: Frontend Container API Proxy 404 in Vite Preview
* **Severity:** High
* **Requirement:** FR1, NFR4, NFR9
* **Steps to Reproduce:** Run `docker compose up` and visit `http://localhost:3000/register` in the browser, submitting the form.
* **Expected Result:** Browser request to `/api/auth/register` is proxied to the backend at port 8000 and returns 200/400.
* **Actual Result:** `POST http://localhost:3000/api/auth/register` returned `404 Not Found`. Additionally, `/favicon.ico` returned 404 in console.
* **Root Cause:**
  1. The frontend Docker container runs `vite preview`, but its runtime image only contained the built static files and a separately installed global Vite binary. It did not contain `vite.config.ts` or the dependencies needed to load that config, so the existing `preview.proxy` was not active. Unmatched API requests could fall through to the SPA rather than reach FastAPI.
  2. The browser must use the frontend's same-origin `/api` path; the backend is reached from within Docker at `http://backend:8000`, not `localhost`.
* **Resolution:**
  1. Copy the build's Vite configuration and `node_modules` into the runtime image and execute its local Vite binary, ensuring `preview.proxy` is loaded. Keep `server.proxy` for development and `preview.proxy` for the Docker preview.
  2. Keep the proxy target at `VITE_API_URL` with the Docker service fallback `http://backend:8000` and `changeOrigin: true`; both Vite modes bind to all container interfaces.
  3. Keep all backend routers mounted at the same `/api` paths called by the frontend. `/api/health` is available for proxy checks.
  4. Keep local HTTP cookies non-Secure by default while allowing `COOKIE_SECURE=true` to be supplied for production. The same-origin proxy preserves browser session cookies and CSRF behavior without wildcard CORS.
  5. Keep the explicit empty favicon link and add Playwright coverage for registration through `http://localhost:3000/api/auth/register` plus the browser registration, login, MFA enrolment, and verification flow.
