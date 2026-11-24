import pyotp
from app.core.config import settings

CSRF_HEADER = {"X-Requested-With": "XMLHttpRequest"}

def test_account_recovery_flow(client):
    email = "recovery_test@example.com"
    password = "InitialPassword123!"

    # 1. Setup account with MFA enabled
    client.post("/api/auth/register", json={"email": email, "password": password}, headers=CSRF_HEADER)
    client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)
    enrol_res = client.post("/api/mfa/enrol/start", headers=CSRF_HEADER)
    secret = enrol_res.json()["secret"]
    code = pyotp.TOTP(secret).now()
    confirm_res = client.post("/api/mfa/enrol/confirm", json={"code": code}, headers=CSRF_HEADER)
    recovery_codes = confirm_res.json()["recovery_codes"]
    assert len(recovery_codes) == 10

    # 2. Sign out (simulating lost authenticator device)
    client.post("/api/auth/logout", headers=CSRF_HEADER)

    # 3. Start recovery with first recovery code
    used_code = recovery_codes[0]
    rec_res = client.post(
        "/api/recovery/start",
        json={"email": email, "recovery_code": used_code},
        headers=CSRF_HEADER
    )
    assert rec_res.status_code == 200
    recovery_token = rec_res.json()["recovery_token"]
    assert recovery_token is not None

    # 4. Attempting to reuse the exact same recovery code must be rejected (A18, NFR5)
    reuse_res = client.post(
        "/api/recovery/start",
        json={"email": email, "recovery_code": used_code},
        headers=CSRF_HEADER
    )
    assert reuse_res.status_code == 400
    assert reuse_res.json()["error"]["code"] == "RECOVERY_FAILED"

    # 5. Complete recovery with new password
    new_password = "BrandNewPassphrase2026!"
    complete_res = client.post(
        "/api/recovery/complete",
        json={"recovery_token": recovery_token, "new_password": new_password},
        headers=CSRF_HEADER
    )
    assert complete_res.status_code == 200
    assert "MFA reset" in complete_res.json()["message"]

    # 6. Verify sign-in with new password (MFA should now be reset to False)
    login_new = client.post(
        "/api/auth/login",
        json={"email": email, "password": new_password},
        headers=CSRF_HEADER
    )
    assert login_new.status_code == 200
    assert login_new.json()["status"] == "authenticated"
    assert login_new.json()["mfa_enabled"] is False

    # Old password must fail
    client.post("/api/auth/logout", headers=CSRF_HEADER)
    login_old = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=CSRF_HEADER
    )
    assert login_old.status_code == 401
