from datetime import datetime, timezone, timedelta
import secrets
import uuid
from typing import Tuple, List, Optional
from sqlalchemy import update
from sqlalchemy.orm import Session
import redis

from app.db.models import User, RecoveryCode, RecoveryToken
from app.core.config import settings
from app.core.security import (
    hash_password,
    dummy_verify_password,
    validate_password_strength,
    hash_identifier,
    hash_recovery_code,
    hash_token,
    generate_recovery_codes_batch
)
from app.core.errors import (
    RecoveryFailedException,
    AccountLockedException,
    NexisAPIException
)
from app.modules.sessions.service import revoke_all_user_sessions
from app.modules.security.rate_limit import check_rate_limit
from app.modules.security.lockout import (
    check_lockout,
    record_failed_attempt,
    reset_lockout
)
from app.modules.security.audit import log_audit_event


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def start_account_recovery(
    db: Session,
    redis_client: redis.Redis,
    email: str,
    recovery_code: str,
    ip: str,
    user_agent: str
) -> str:
    """
    Validate recovery code and issue short-lived recovery token (FR7, NFR5, FR11, A18).
    Consumes code atomically exactly once.
    Returns raw recovery_token string.
    """
    normalized_email = email.strip().lower()
    account_hash = hash_identifier(normalized_email)

    # Rate limiting & Lockout
    check_rate_limit(redis_client, "recovery_ip", ip, limit=settings.rate_limit_recovery_per_minute, window_seconds=60)
    check_rate_limit(redis_client, "recovery_account", account_hash, limit=settings.rate_limit_recovery_per_minute, window_seconds=60)
    check_lockout(redis_client, account_hash, ip)

    user = db.query(User).filter(User.email == normalized_email).first()
    code_hash = hash_recovery_code(recovery_code)
    now = datetime.now(timezone.utc)

    if not user:
        # Unknown account: dummy hash timing equalization (FR11)
        dummy_verify_password("dummy_recovery_attempt")
        _, locked_ttl = record_failed_attempt(redis_client, account_hash, ip)
        log_audit_event(
            db=db,
            event_type="recovery_start_failed",
            outcome="failure",
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            details={"reason": "User not found"}
        )
        if locked_ttl:
            raise AccountLockedException(retry_after_seconds=locked_ttl)
        raise RecoveryFailedException()

    # Atomic consumption: UPDATE ... WHERE user_id = :id AND code_hash = :hash AND used_at IS NULL (NFR5)
    stmt = (
        update(RecoveryCode)
        .where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == code_hash,
            RecoveryCode.used_at.is_(None)
        )
        .values(used_at=now)
    )
    result = db.execute(stmt)
    db.commit()

    if result.rowcount == 0:
        # Invalid code or already consumed
        _, locked_ttl = record_failed_attempt(redis_client, account_hash, ip)
        log_audit_event(
            db=db,
            event_type="recovery_start_failed",
            outcome="failure",
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            details={"reason": "Invalid or already used recovery code"}
        )
        if locked_ttl:
            raise AccountLockedException(retry_after_seconds=locked_ttl)
        raise RecoveryFailedException()

    # Success: code consumed. Reset lockout counter
    reset_lockout(redis_client, account_hash, ip)

    # Issue single-use recovery token valid for 15 minutes
    raw_recovery_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_recovery_token)
    expires_at = now + timedelta(minutes=settings.recovery_token_minutes)

    recovery_token_record = RecoveryToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used_at=None,
        created_at=now
    )
    db.add(recovery_token_record)
    db.commit()

    log_audit_event(
        db=db,
        event_type="recovery_code_used",
        outcome="success",
        user_id=user.id,
        email=normalized_email,
        ip=ip,
        user_agent=user_agent
    )

    return raw_recovery_token


def complete_account_recovery(
    db: Session,
    recovery_token: str,
    new_password: str,
    ip: str,
    user_agent: str
) -> None:
    """
    Set new password, reset MFA, and invalidate all sessions and remaining recovery codes (FR7, A19).
    """
    valid, err_msg = validate_password_strength(new_password)
    if not valid:
        raise NexisAPIException(status_code=400, code="WEAK_PASSWORD", message=err_msg)

    token_hash = hash_token(recovery_token)
    now = datetime.now(timezone.utc)

    # Validate recovery token atomically
    token_record = db.query(RecoveryToken).filter(
        RecoveryToken.token_hash == token_hash,
        RecoveryToken.used_at.is_(None)
    ).first()

    if not token_record or (token_record.expires_at and now > _to_utc(token_record.expires_at)):
        raise NexisAPIException(
            status_code=400,
            code="INVALID_RECOVERY_TOKEN",
            message="The recovery token is invalid or has expired. Please restart account recovery."
        )

    # Mark token used
    token_record.used_at = now

    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise NexisAPIException(status_code=404, code="USER_NOT_FOUND", message="User not found.")

    # 1. Update password with Argon2id
    user.password_hash = hash_password(new_password)

    # 2. Reset MFA (clear secret, disable MFA, clear totp step)
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_pending_secret_encrypted = None
    user.last_totp_step = None

    # 3. Invalidate all remaining recovery codes for this user
    db.query(RecoveryCode).filter(
        RecoveryCode.user_id == user.id,
        RecoveryCode.used_at.is_(None)
    ).update({"used_at": now})

    # 4. Revoke all active sessions for this user (FR8)
    revoke_all_user_sessions(db, user.id)

    db.commit()

    log_audit_event(
        db=db,
        event_type="account_recovery_completed",
        outcome="success",
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent,
        details={"mfa_reset": True, "sessions_revoked": True}
    )


def regenerate_user_recovery_codes(
    db: Session,
    user: User,
    ip: str,
    user_agent: str
) -> List[str]:
    """Regenerate 10 recovery codes for authenticated user with MFA enabled (FR6)."""
    if not user.mfa_enabled:
        raise NexisAPIException(
            status_code=400,
            code="MFA_NOT_ENABLED",
            message="Multi-factor authentication must be enabled before generating recovery codes."
        )

    now = datetime.now(timezone.utc)

    # Invalidate all prior recovery codes
    db.query(RecoveryCode).filter(
        RecoveryCode.user_id == user.id,
        RecoveryCode.used_at.is_(None)
    ).update({"used_at": now})

    # Generate 10 new codes
    new_codes = generate_recovery_codes_batch(10)
    for code in new_codes:
        code_hash = hash_recovery_code(code)
        rec = RecoveryCode(
            id=uuid.uuid4(),
            user_id=user.id,
            code_hash=code_hash,
            used_at=None,
            created_at=now
        )
        db.add(rec)

    db.commit()

    log_audit_event(
        db=db,
        event_type="recovery_codes_regenerated",
        outcome="success",
        user_id=user.id,
        email=user.email,
        ip=ip,
        user_agent=user_agent,
        details={"count": 10}
    )

    return new_codes
