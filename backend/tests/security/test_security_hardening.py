import pyotp
import pytest
from app.core.config import settings
from app.core.errors import NexisAPIException

CSRF_HEADER = {"X-Requested-With": "XMLHttpRequest"}

def test_brute_force_lockout_trigger(client):
    email = "brute_target@example.com"
    password = "CorrectPassword123"

    # Register user
    client.post("/api/auth/register", json={"email": email, "password": password}, headers=CSRF_HEADER)

    # 4 failed attempts: generic 401
    for _ in range(4):
        res = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword"}, headers=CSRF_HEADER)
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    # 5th failed attempt: triggers lockout (HTTP 429)
    res_lock = client.post("/api/auth/login", json={"email": email, "password": "WrongPassword"}, headers=CSRF_HEADER)
    assert res_lock.status_code == 429
    assert res_lock.json()["error"]["code"] == "ACCOUNT_LOCKED"
    assert "Retry-After" in res_lock.headers
    assert "temporarily locked" in res_lock.json()["error"]["message"]


def test_generic_error_enumeration_protection(client):
    """Verify that unknown email and wrong password produce identical generic responses (FR11)."""
    # 1. Unknown user
    res1 = client.post(
        "/api/auth/login",
        json={"email": "nonexistent_random_user@example.com", "password": "SomePassword123"},
        headers=CSRF_HEADER
    )
    # 2. Existing user, wrong password
    client.post("/api/auth/register", json={"email": "known_user@example.com", "password": "RealPassword123"}, headers=CSRF_HEADER)
    res2 = client.post(
        "/api/auth/login",
        json={"email": "known_user@example.com", "password": "WrongPassword123"},
        headers=CSRF_HEADER
    )

    assert res1.status_code == 401
    assert res2.status_code == 401
    assert res1.json() == res2.json()
    assert res1.json()["error"]["message"] == "Invalid email or password. Please check your credentials and try again."


def test_mfa_pending_blocked_from_protected_resources(client):
    """MFA_PENDING session must not access any protected resource (FR2)."""
    email = "mfa_pending_user@example.com"
    password = "MyPassword123!"

    # Setup MFA
    client.post("/api/auth/register", json={"email": email, "password": password}, headers=CSRF_HEADER)
    client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)
    enrol_res = client.post("/api/mfa/enrol/start", headers=CSRF_HEADER)
    secret = enrol_res.json()["secret"]
    code = pyotp.TOTP(secret).now()
    client.post("/api/mfa/enrol/confirm", json={"code": code}, headers=CSRF_HEADER)
    client.post("/api/auth/logout", headers=CSRF_HEADER)

    # Login to create MFA_PENDING session
    client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)

    # Attempt to call protected endpoints
    # 1. enrol start
    blocked_res1 = client.post("/api/mfa/enrol/start", headers=CSRF_HEADER)
    assert blocked_res1.status_code == 401
    assert blocked_res1.json()["error"]["code"] == "MFA_REQUIRED"

    # 2. regenerate recovery codes
    blocked_res2 = client.post("/api/recovery/regenerate", headers=CSRF_HEADER)
    assert blocked_res2.status_code == 401
    assert blocked_res2.json()["error"]["code"] == "MFA_REQUIRED"
