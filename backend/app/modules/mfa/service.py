import io
import time
import base64
import uuid
from typing import Tuple, List, Optional
import pyotp
import qrcode
from sqlalchemy import update
from sqlalchemy.orm import Session
import redis

from app.db.models import User, SessionModel, SessionState, RecoveryCode
from app.core.config import settings
from app.core.security import (
    encrypt_totp_secret,
    decrypt_totp_secret,
    generate_recovery_codes_batch,
    hash_recovery_code,
    hash_identifier
)
from app.core.errors import (
    MfaInvalidCodeException,
    AccountLockedException,
    NexisAPIException
)
from app.modules.sessions.service import rotate_session
from app.modules.security.rate_limit import check_rate_limit
from app.modules.security.lockout import (
    check_lockout,
    record_failed_attempt,
    reset_lockout
)
from app.modules.security.audit import log_audit_event


def format_grouped_secret(secret: str) -> str:
    """Format base32 secret in blocks of 4 characters for screen reader ease (FR3, A14)."""
    clean = secret.replace(" ", "").upper()
    return " ".join(clean[i:i+4] for i in range(0, len(clean), 4))


def generate_qr_data_uri(otpauth_uri: str) -> str:
    """Generate QR code PNG as base64 data URI for optional visual scanning (FR3, A14)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(otpauth_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_img}"


def start_mfa_enrolment(
    db: Session,
    user: User,
    ip: str,
    user_agent: str
) -> Tuple[str, str, str, str]:
    """
    Generate new base32 secret, encrypt at rest, and prepare manual & QR setup (FR3, A14, A41).
    Returns (raw_secret, grouped_secret, otpauth_uri, qr_data_uri).
    """
    raw_secret = pyotp.random_base32()
    encrypted_secret = encrypt_totp_secret(raw_secret)

    # Store encrypted pending secret
    user.mfa_pending_secret_encrypted = encrypted_secret
    db.commit()

    grouped_secret = format_grouped_secret(raw_secret)
    totp = pyotp.TOTP(raw_secret)
    otpauth_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="Nexis"
    )
    qr_data_uri = generate_qr_data_uri(otpauth_uri)

    log_audit_event(
        db=db,
        event_type="mfa_enrol_start",
        outcome="success",
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent
    )

    return raw_secret, grouped_secret, otpauth_uri, qr_data_uri


def confirm_mfa_enrolment(
    db: Session,
    redis_client: redis.Redis,
    user: User,
    submitted_code: str,
    ip: str,
    user_agent: str
) -> List[str]:
    """
    Confirm enrolment by verifying a code against the pending secret (FR4, FR6, A17).
    On success: moves secret to active, sets last_totp_step, generates 10 recovery codes.
    """
    if not user.mfa_pending_secret_encrypted:
        raise NexisAPIException(
            status_code=400,
            code="NO_PENDING_ENROLMENT",
            message="No pending MFA enrolment found. Please restart MFA setup."
        )

    # Rate limit confirmation attempts
    check_rate_limit(redis_client, "mfa_enrol_confirm", str(user.id), limit=10, window_seconds=60)

    clean_code = submitted_code.replace(" ", "").strip()
    pending_secret = decrypt_totp_secret(user.mfa_pending_secret_encrypted)
    totp = pyotp.TOTP(pending_secret)

    # Verify code with +/- 1 step drift window (FR5, RFC 6238)
    if not totp.verify(clean_code, valid_window=1):
        log_audit_event(
            db=db,
            event_type="mfa_enrol_confirm",
            outcome="failure",
            user_id=user.id,
            email=user.email,
            ip=ip,
            user_agent=user_agent
        )
        raise MfaInvalidCodeException(
            "The 6-digit code does not match. Please ensure your authenticator app time is synchronized and try again."
        )

    # Enrolment confirmed: activate MFA
    now_step = int(time.time() // 30)
    user.mfa_enabled = True
    user.mfa_secret_encrypted = user.mfa_pending_secret_encrypted
    user.mfa_pending_secret_encrypted = None
    user.last_totp_step = now_step

    # Generate 10 one-time recovery codes (FR6, A17)
    plaintext_recovery_codes = generate_recovery_codes_batch(10)

    # Invalidate any old recovery codes for this user
    db.query(RecoveryCode).filter(RecoveryCode.user_id == user.id).delete()

    # Store hashed recovery codes only (NFR3, A16)
    for code in plaintext_recovery_codes:
        code_hash = hash_recovery_code(code)
        rec = RecoveryCode(
            id=uuid.uuid4(),
            user_id=user.id,
            code_hash=code_hash,
            used_at=None
        )
        db.add(rec)

    db.commit()

    log_audit_event(
        db=db,
        event_type="mfa_enrol_confirm",
        outcome="success",
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent,
        details={"codes_generated": 10}
    )

    return plaintext_recovery_codes


def verify_totp_code(
    db: Session,
    redis_client: redis.Redis,
    user: User,
    session_record: SessionModel,
    submitted_code: str,
    ip: str,
    user_agent: str
) -> Tuple[str, SessionModel]:
    """
    Verify TOTP code for MFA_PENDING session (FR5, NFR5, A42).
    Enforces atomic replay protection under concurrent requests.
    Rotates session to AUTHENTICATED on success.
    """
    account_hash = hash_identifier(user.email)

    # 1. Rate limiting & Lockout check
    check_rate_limit(redis_client, "totp_verify_ip", ip, limit=settings.rate_limit_mfa_per_minute, window_seconds=60)
    check_rate_limit(redis_client, "totp_verify_account", account_hash, limit=settings.rate_limit_mfa_per_minute, window_seconds=60)
    check_lockout(redis_client, account_hash, ip)

    if not user.mfa_secret_encrypted:
        raise NexisAPIException(status_code=400, code="MFA_NOT_CONFIGURED", message="MFA is not configured on this account.")

    clean_code = submitted_code.replace(" ", "").strip()
    active_secret = decrypt_totp_secret(user.mfa_secret_encrypted)
    totp = pyotp.TOTP(active_secret)

    now_step = int(time.time() // 30)
    matched_step = None
    for step_offset in [0, 1, -1]:
        test_step = now_step + step_offset
        if totp.at(test_step * 30) == clean_code:
            matched_step = test_step
            break

    if matched_step is None:
        # Invalid code: record failed attempt toward lockout
        _, locked_ttl = record_failed_attempt(redis_client, account_hash, ip)
        log_audit_event(
            db=db,
            event_type="totp_verify_failed",
            outcome="failure",
            user_id=user.id,
            email=user.email,
            ip=ip,
            user_agent=user_agent,
            details={"reason": "Invalid code"}
        )
        if locked_ttl:
            raise AccountLockedException(retry_after_seconds=locked_ttl)
        raise MfaInvalidCodeException("Invalid one-time verification code. Please check your authenticator app and try again.")

    # 2. Atomic Replay Protection (NFR5, A42)
    # Ensure this time step (or older) has not already been used.
    stmt = (
        update(User)
        .where(
            User.id == user.id,
            (User.last_totp_step.is_(None)) | (User.last_totp_step < matched_step)
        )
        .values(last_totp_step=matched_step)
    )
    result = db.execute(stmt)
    db.commit()

    if result.rowcount == 0:
        # Replay attempt: already accepted for this time-step
        _, locked_ttl = record_failed_attempt(redis_client, account_hash, ip)
        log_audit_event(
            db=db,
            event_type="totp_replay_rejected",
            outcome="failure",
            user_id=user.id,
            email=user.email,
            ip=ip,
            user_agent=user_agent,
            details={"attempted_step": matched_step}
        )
        if locked_ttl:
            raise AccountLockedException(retry_after_seconds=locked_ttl)
        raise MfaInvalidCodeException("This code was already used. Please wait for your authenticator app to display the next code.")

    # 3. Successful verification: clear failed lockout attempts
    reset_lockout(redis_client, account_hash, ip)

    # 4. Rotate session from MFA_PENDING to AUTHENTICATED (FR8)
    new_raw_token, new_session = rotate_session(
        db=db,
        old_token_hash=session_record.id,
        user_id=user.id,
        new_state=SessionState.AUTHENTICATED
    )

    log_audit_event(
        db=db,
        event_type="totp_verify_success",
        outcome="success",
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent
    )

    return new_raw_token, new_session
