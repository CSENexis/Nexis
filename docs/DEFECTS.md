# Nexis Defects Log (docs/DEFECTS.md)

This log records every defect, security finding, and design discrepancy discovered during independent testing of the **Nexis Multi-Factor Authentication System for Visually Impaired Users**, following the QA and Security-Test Engineer guidelines.

---

## Defect Summary Table

| Defect ID | Severity | Requirement | Description | Status | Fix Commit / Note |
|---|---|---|---|---|---|
| DEF-001 | Low | Maintainability | Import path in `frontend/src/main.tsx` used `.tsx` extension, causing TypeScript build error | Fixed | Commit `d14adcd` |
| DEF-002 | Medium | Maintainability | Missing `Optional` type import in `backend/app/modules/auth/router.py` | Fixed | Commit `8c95dce` |
| DEF-003 | Medium | Concurrency (NFR5) | SQLite in-memory test runner thread pool contention on synchronous TestClient | Fixed | Configured isolated test sessions per thread |
| DEF-004 | Low | Environment | Windows Application Control policy blocked SQLAlchemy 2.1 Cython DLL; pinned SQLAlchemy to <2.1.0 pure-python compatible | Resolved | Pinned `sqlalchemy>=2.0.28,<2.1.0` in `requirements.txt` |
| DEF-005 | Info | NFR9 | Local Docker daemon unavailable in current Windows sandbox environment; verified via standalone native test runner and Dockerfile validation | Documented | Documented in `docs/TEST_REPORT.md` |

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
* **Resolution:** Ensure test fixtures initialize independent connection transactions or thread-safe isolation.
