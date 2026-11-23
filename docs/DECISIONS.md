# Architectural and Design Decisions (docs/DECISIONS.md)

This document records the architectural and security decisions, trade-offs, and resolutions between project specifications and design documents for the **Nexis Multi-Factor Authentication System for Visually Impaired Users**.

---

## 1. User Registration (FR1, A2 Resolution)
* **Conflict / Question:** Assumption A2 states *"No registered users; no admin role required"*, implying accounts might be pre-seeded. However, Section 5.1 of the Project Completion Prompt and real-world demonstration require a user registration endpoint (`POST /api/auth/register`).
* **Decision:** Implement `POST /api/auth/register` to allow self-service registration for demonstration, lecturer review, and automated end-to-end testing.
* **Security Control:** Email addresses are normalized to lowercase. Passwords must be at least 8 characters long and are validated against a blocklist of weak/common passwords (NIST SP 800-63B). Responses return generic success confirmation without revealing if an account already exists to prevent enumeration.

---

## 2. Password Hashing Algorithm and Parameters (FR1, NFR3, A8)
* **Decision:** Argon2id via `argon2-cffi` using current OWASP guidelines:
  * Time cost (`time_cost` / iterations): 3
  * Memory cost (`memory_cost`): 65536 KiB (64 MiB)
  * Parallelism (`parallelism`): 4 threads
  * Hash length: 32 bytes, Salt length: 16 bytes
* **Constant Timing:** When a login attempt specifies an unregistered email, a dummy Argon2id hash is computed using a static dummy hash to equalize response latency and prevent user enumeration timing attacks.

---

## 3. Session Management vs. JWTs (FR8, A10, A37, A40)
* **Decision:** Server-side sessions stored in PostgreSQL, referenced by a secure, random 256-bit token issued via an `HttpOnly` cookie (`nexis_session`).
* **Rationale:** JWTs cannot be revoked instantly without complex distributed blacklists. Server-side session records allow immediate revocation on logout, account recovery, password change, or suspected compromise.
* **Token Protection:** The raw 256-bit token is sent only in the secure HttpOnly cookie. The database stores only the SHA-256 hash of the token (`id` column), ensuring a database read leak does not grant session access.
* **Expirations:**
  * **Idle Expiration:** 30 minutes of inactivity updates `idle_expires_at` on each authenticated request.
  * **Absolute Expiration:** 8 hours maximum lifetime (`absolute_expires_at`), after which re-authentication is mandatory.
  * **Privilege Separation:** Password authentication yields a session in `MFA_PENDING` state if MFA is enabled. Only after successful TOTP verification is the session rotated and upgraded to `AUTHENTICATED`.

---

## 4. TOTP Secret Encryption at Rest (FR3, NFR3, A41)
* **Decision:** TOTP shared secrets are encrypted at rest in the PostgreSQL database using Fernet symmetric encryption (`cryptography.fernet.Fernet`), deriving the cipher from `TOTP_ENC_KEY` in environment variables.
* **Key Lifecycle:** The plaintext secret is revealed to the user **exactly once** during the enrolment phase. Once confirmed, the secret remains encrypted in `mfa_secret_encrypted`. It is never returned in any subsequent API response or included in logs.

---

## 5. TOTP Verification and Replay Prevention (FR5, NFR5, A42)
* **Decision:** TOTP verification conforms to RFC 6238:
  * 6 digits, 30-second time step, SHA-1 HMAC (standard authenticator app compatibility).
  * Allowed drift window: $\pm 1$ step (30 seconds before and after) to tolerate mobile clock drift.
* **Atomic Replay Prevention:** To satisfy NFR5 under high concurrency, replay protection is implemented at the database level using an atomic conditional update:
  ```sql
  UPDATE users
  SET last_totp_step = :current_step
  WHERE id = :user_id AND (last_totp_step IS NULL OR last_totp_step < :current_step);
  ```
  If zero rows are affected, the verification fails immediately because the token for that time step (or an earlier one) was already consumed.

---

## 6. Recovery Code Format, Storage, and Atomicity (FR6, FR7, NFR5, A15–A18)
* **Decision:**
  * 10 recovery codes generated per MFA enrolment using Python `secrets.choice`.
  * Format: 12-character alphanumeric divided into 3 groups of 4 (`XXXX-XXXX-XXXX`), omitting visually and phonetically confusing characters (`0`, `O`, `1`, `I`, `L`).
  * Storage: Codes are hashed using SHA-256 with an HMAC key (`HMAC_KEY`). The plaintext code is displayed once to the user upon enrolment.
* **Atomic Single-Use:**
  ```sql
  UPDATE recovery_codes
  SET used_at = :now
  WHERE user_id = :user_id AND code_hash = :code_hash AND used_at IS NULL;
  ```
  If zero rows are updated, the code is invalid or already consumed.
* **Account Reset on Recovery:** Using a recovery code issues a short-lived, single-use `recovery_token`. Setting a new password revokes all active sessions, resets MFA status (`mfa_enabled = false`), clears old TOTP secrets, and invalidates all remaining recovery codes.

---

## 7. Rate Limiting, Temporary Lockout, and Denial-of-Service Defense (FR9, A24, A25)
* **Decision:** Redis TTL-based counters.
  * Rate limits apply to: `/api/auth/login`, `/api/auth/register`, `/api/mfa/verify`, `/api/recovery/start`.
  * Lockout triggers after 5 consecutive failed attempts on an account within a 15-minute window.
  * Counter keys are scoped to both `ip` and `account_identifier_hash` to prevent distributed brute-force attacks while mitigating denial-of-service against legitimate users from shared IP addresses.
  * Locked responses return HTTP 429 / 401 with `Retry-After: <seconds>` and a clear, screen-reader friendly text message stating the wait duration.
  * **Fail-Closed Policy (NFR6):** If Redis becomes unreachable, authentication endpoints fail closed (deny request) to prevent bypassing rate limiting and lockout safeguards.

---

## 8. CSRF Protection for Cookie-based Sessions (FR8)
* **Decision:** Because cookies use `SameSite=Lax` or `SameSite=Strict`, we enforce custom request header validation (`X-Requested-With: XMLHttpRequest` or `X-CSRF-Token`) for all state-changing endpoints (`POST`, `PUT`, `DELETE`). Modern browsers restrict cross-origin requests from setting custom headers without CORS preflight approval.

---

## 9. Accessibility-First Design (FR3, FR10, NFR1, NFR2, A14, A29)
* **Decision:**
  * Visual CAPTCHA is completely omitted (A23).
  * MFA enrolment prioritizes the **text secret**: displayed in large readable font, formatted in 4-character chunks, accompanied by an accessible "Copy Secret" button that triggers an ARIA live region announcement.
  * Step-by-step instructions provide explicit instructions for manual key entry in Google Authenticator, Microsoft Authenticator, and 2FAS.
  * QR Code is optional secondary visual aid, hidden or collapsed by default for screen readers, with complete `alt` description explaining that the text secret provides identical functionality.
  * All error and status messages are announced via persistent ARIA live regions (`role="alert"` and `role="status"`).
  * Route changes programmatically move focus to the primary `<h1>` heading with `tabIndex={-1}` and update `document.title`.
  * Keyboard navigation adheres to WCAG 2.1 AA with minimum 3:1 focus ring contrast and 4.5:1 text contrast.
