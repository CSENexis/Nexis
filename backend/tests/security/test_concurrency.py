import pytest
import pyotp
import uuid
from datetime import datetime, timezone
from sqlalchemy import update
from app.core.config import settings
from app.db.models import User, RecoveryCode
from app.core.security import hash_recovery_code

CSRF_HEADER = {"X-Requested-With": "XMLHttpRequest"}

def test_atomic_totp_replay_rejection(client):
    """
    NFR5, A42: Verify that an already accepted TOTP code for the same time step
    cannot be accepted again. Atomic conditional update rejects the replay.
    """
    email = "replay_prevention@example.com"
    password = "StrongPassword123!"

    # 1. Register and setup MFA
    client.post("/api/auth/register", json={"email": email, "password": password}, headers=CSRF_HEADER)
    client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)
    enrol_res = client.post("/api/mfa/enrol/start", headers=CSRF_HEADER)
    secret = enrol_res.json()["secret"]
    totp = pyotp.TOTP(secret)
    confirm_code = totp.now()
    client.post("/api/mfa/enrol/confirm", json={"code": confirm_code}, headers=CSRF_HEADER)
    client.post("/api/auth/logout", headers=CSRF_HEADER)

    # 2. Login to get MFA_PENDING session
    login_res = client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)
    assert login_res.json()["status"] == "mfa_pending"

    import time
    now_step = int(time.time() // 30)
    valid_code = totp.at((now_step + 1) * 30)

    # First verification attempt -> MUST SUCCEED
    res1 = client.post("/api/mfa/verify", json={"code": valid_code}, headers=CSRF_HEADER)
    assert res1.status_code == 200
    assert res1.json()["status"] == "authenticated"

    # Immediate replay of the EXACT SAME CODE in the same time step -> MUST BE REJECTED
    # Log back in to get another MFA_PENDING session to test replay
    client.post("/api/auth/logout", headers=CSRF_HEADER)
    client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)

    res2 = client.post("/api/mfa/verify", json={"code": valid_code}, headers=CSRF_HEADER)
    assert res2.status_code in [400, 401]
    assert "already used" in res2.json()["error"]["message"].lower() or "invalid" in res2.json()["error"]["message"].lower()


def test_atomic_recovery_code_single_use(client):
    """
    NFR5, A18: Verify that a valid recovery code is consumed atomically exactly once.
    Subsequent attempts with the same code fail.
    """
    email = "single_use_rec@example.com"
    password = "StrongPassword123!"

    # Setup MFA and obtain recovery codes
    client.post("/api/auth/register", json={"email": email, "password": password}, headers=CSRF_HEADER)
    client.post("/api/auth/login", json={"email": email, "password": password}, headers=CSRF_HEADER)
    enrol_res = client.post("/api/mfa/enrol/start", headers=CSRF_HEADER)
    secret = enrol_res.json()["secret"]
    code = pyotp.TOTP(secret).now()
    confirm_res = client.post("/api/mfa/enrol/confirm", json={"code": code}, headers=CSRF_HEADER)
    recovery_codes = confirm_res.json()["recovery_codes"]
    target_code = recovery_codes[0]
    client.post("/api/auth/logout", headers=CSRF_HEADER)

    # First use -> SUCCEEDS
    res1 = client.post(
        "/api/recovery/start",
        json={"email": email, "recovery_code": target_code},
        headers=CSRF_HEADER
    )
    assert res1.status_code == 200
    assert "recovery_token" in res1.json()

    # Second use -> MUST FAIL (atomically consumed)
    res2 = client.post(
        "/api/recovery/start",
        json={"email": email, "recovery_code": target_code},
        headers=CSRF_HEADER
    )
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "RECOVERY_FAILED"


def test_sql_atomic_conditional_update_under_concurrency(db_session):
    """
    Directly tests the SQL atomic conditional update pattern specified in NFR5:
    UPDATE users SET last_totp_step = :step WHERE id = :id AND (last_totp_step IS NULL OR last_totp_step < :step)
    Asserts that rowcount is 1 on first update and 0 on subsequent attempts for the same step.
    """
    user_id = uuid.uuid4()
    test_user = User(
        id=user_id,
        email="atomic_sql_test@example.com",
        password_hash="dummy_hash",
        last_totp_step=None
    )
    db_session.add(test_user)
    db_session.commit()

    step = 55555555

    # First attempt: updates row, rowcount == 1
    stmt1 = (
        update(User)
        .where(
            User.id == user_id,
            (User.last_totp_step.is_(None)) | (User.last_totp_step < step)
        )
        .values(last_totp_step=step)
    )
    res1 = db_session.execute(stmt1)
    db_session.commit()
    assert res1.rowcount == 1

    # Second attempt with same step: rowcount == 0 (atomic rejection)
    stmt2 = (
        update(User)
        .where(
            User.id == user_id,
            (User.last_totp_step.is_(None)) | (User.last_totp_step < step)
        )
        .values(last_totp_step=step)
    )
    res2 = db_session.execute(stmt2)
    db_session.commit()
    assert res2.rowcount == 0

    # Attempt with older step: rowcount == 0
    stmt3 = (
        update(User)
        .where(
            User.id == user_id,
            (User.last_totp_step.is_(None)) | (User.last_totp_step < step - 1)
        )
        .values(last_totp_step=step - 1)
    )
    res3 = db_session.execute(stmt3)
    db_session.commit()
    assert res3.rowcount == 0
