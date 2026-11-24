from app.core.config import settings

CSRF_HEADER = {"X-Requested-With": "XMLHttpRequest"}

def test_registration_and_login_flow(client):
    email = "testuser@example.com"
    password = "CorrectHorseBatteryStaple123"

    # 1. Register
    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password},
        headers=CSRF_HEADER
    )
    assert reg_res.status_code == 200
    assert "created successfully" in reg_res.json()["message"]

    # 2. Login (MFA not yet enabled -> AUTHENTICATED)
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers=CSRF_HEADER
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["status"] == "authenticated"
    assert login_data["mfa_enabled"] is False
    assert settings.cookie_name in login_res.cookies

    # 3. GET /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["status"] == "authenticated"
    assert me_data["email"] == email

    # 4. Logout
    logout_res = client.post("/api/auth/logout", headers=CSRF_HEADER)
    assert logout_res.status_code == 200

    # 5. Verify unauthenticated after logout
    me_after = client.get("/api/auth/me")
    assert me_after.json()["status"] == "unauthenticated"


def test_csrf_protection_on_post(client):
    # State-changing POST without CSRF header should be rejected
    res = client.post(
        "/api/auth/register",
        json={"email": "csrf_test@example.com", "password": "StrongPassword123"}
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CSRF_FAILED"
