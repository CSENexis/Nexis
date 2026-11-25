import pyotp
from app.core.config import settings

CSRF_HEADER = {"X-Requested-With": "XMLHttpRequest"}

def test_full_totp_enrolment_and_verification_flow(client):
    email = "totp_user@example.com"
    password = "SecurePassword2026!"

    # 1. Register and sign in
    client.post("/api/auth/register", json={"email": email, "password": password}, headers=CSRF_HEADER)
    client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)

    # 2. Start MFA enrolment
    enrol_res = client.post("/api/mfa/enrol/start", headers=CSRF_HEADER)
    assert enrol_res.status_code == 200
    enrol_data = enrol_res.json()
    secret = enrol_data["secret"]
    assert secret is not None
    assert "secret_grouped" in enrol_data
    assert "otpauth_uri" in enrol_data
    assert "qr_code_data_uri" in enrol_data

    # 3. Confirm MFA enrolment using TOTP code
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    confirm_res = client.post(
        "/api/mfa/enrol/confirm",
        json={"code": valid_code},
        headers=CSRF_HEADER
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    recovery_codes = confirm_data["recovery_codes"]
    assert len(recovery_codes) == 10

    # 4. Sign out
    client.post("/api/auth/logout", headers=CSRF_HEADER)

    # 5. Sign in again -> Password step should now produce MFA_PENDING session (FR2)
    login_res2 = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=CSRF_HEADER
    )
    assert login_res2.status_code == 200
    assert login_res2.json()["status"] == "mfa_pending"

    # GET /me must return mfa_pending
    me_res = client.get("/api/auth/me")
    assert me_res.json()["status"] == "mfa_pending"

    # 6. Verify MFA using TOTP (step + 1 within allowed drift window)
    import time
    now_step = int(time.time() // 30)
    verify_code = totp.at((now_step + 1) * 30)
    verify_res = client.post(
        "/api/mfa/verify",
        json={"code": verify_code},
        headers=CSRF_HEADER
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "authenticated"

    # GET /me must now be authenticated
    assert client.get("/api/auth/me").json()["status"] == "authenticated"

    # 7. Replay rejection: Re-submitting the exact same TOTP code must be rejected (FR5, A42)
    replay_res = client.post(
        "/api/mfa/verify",
        json={"code": verify_code},
        headers=CSRF_HEADER
    )
    # Replay is rejected
    assert replay_res.status_code in [400, 401]
