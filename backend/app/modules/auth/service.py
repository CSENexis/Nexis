import uuid
from typing import Tuple, Optional
from sqlalchemy.orm import Session
import redis
from app.db.models import User, SessionModel, SessionState
from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    dummy_verify_password,
    validate_password_strength,
    hash_identifier
)
from app.core.errors import (
    AuthenticationFailedException,
    AccountLockedException,
    NexisAPIException
)
from app.modules.sessions.service import create_session, revoke_session
from app.modules.security.rate_limit import check_rate_limit
from app.modules.security.lockout import (
    check_lockout,
    record_failed_attempt,
    reset_lockout
)
from app.modules.security.audit import log_audit_event


def register_user(
    db: Session,
    redis_client: redis.Redis,
    email: str,
    password: str,
    ip: str,
    user_agent: str
) -> Tuple[bool, str]:
    """
    Register a new user (FR1, A2, A39).
    Generic response prevents account enumeration (FR11).
    """
    # Rate limit registrations per IP
    check_rate_limit(redis_client, "register_ip", ip, limit=10, window_seconds=60)

    # Validate password strength (NIST SP 800-63B)
    valid, err_msg = validate_password_strength(password)
    if not valid:
        raise NexisAPIException(status_code=400, code="WEAK_PASSWORD", message=err_msg)

    normalized_email = email.strip().lower()
    existing_user = db.query(User).filter(User.email == normalized_email).first()

    if existing_user:
        # Generic response: do not reveal if account already exists (FR11)
        log_audit_event(
            db=db,
            event_type="user_registration_duplicate_attempt",
            outcome="failure",
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            details={"reason": "Email already registered"}
        )
        return False, "If the email is valid and available, an account has been created. You can now sign in."

    # Hash password using Argon2id (NFR3, A8)
    hashed = hash_password(password)
    new_user = User(
        id=uuid.uuid4(),
        email=normalized_email,
        password_hash=hashed,
        mfa_enabled=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit_event(
        db=db,
        event_type="user_registered",
        outcome="success",
        user_id=new_user.id,
        email=normalized_email,
        ip=ip,
        user_agent=user_agent
    )

    return True, "Account created successfully. You can now sign in."


def authenticate_user(
    db: Session,
    redis_client: redis.Redis,
    email: str,
    password: str,
    ip: str,
    user_agent: str
) -> Tuple[str, SessionModel, str, User]:
    """
    Authenticate user via email and password (FR1, FR2, FR9, FR11, A8, A9, A24, A25).
    Returns (raw_session_token, session_record, status_string, user).
    """
    normalized_email = email.strip().lower()
    account_hash = hash_identifier(normalized_email)

    # 1. Rate limiting by IP and by account hash
    check_rate_limit(
        redis_client,
        "login_ip",
        ip,
        limit=settings.rate_limit_login_per_minute,
        window_seconds=60
    )
    check_rate_limit(
        redis_client,
        "login_account",
        account_hash,
        limit=settings.rate_limit_login_per_minute,
        window_seconds=60
    )

    # 2. Check temporary lockout
    check_lockout(redis_client, account_hash, ip)

    # 3. Lookup user
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        # User not found: run dummy Argon2id hash to equalize timing (FR1, FR11)
        dummy_verify_password(password)

        # Record failed attempt toward lockout
        _, locked_ttl = record_failed_attempt(redis_client, account_hash, ip)
        log_audit_event(
            db=db,
            event_type="login_failed",
            outcome="failure",
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            details={"reason": "User not found"}
        )
        if locked_ttl:
            log_audit_event(
                db=db,
                event_type="lockout_triggered",
                outcome="failure",
                email=normalized_email,
                ip=ip,
                user_agent=user_agent
            )
            raise AccountLockedException(retry_after_seconds=locked_ttl)

        raise AuthenticationFailedException()

    # 4. Verify password
    if not verify_password(password, user.password_hash):
        _, locked_ttl = record_failed_attempt(redis_client, account_hash, ip)
        log_audit_event(
            db=db,
            event_type="login_failed",
            outcome="failure",
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent,
            details={"reason": "Invalid password"}
        )
        if locked_ttl:
            log_audit_event(
                db=db,
                event_type="lockout_triggered",
                outcome="failure",
                user_id=user.id,
                email=normalized_email,
                ip=ip,
                user_agent=user_agent
            )
            raise AccountLockedException(retry_after_seconds=locked_ttl)

        raise AuthenticationFailedException()

    # 5. Password verified: reset failure counter
    reset_lockout(redis_client, account_hash, ip)

    # 6. Check MFA requirement (FR2)
    if user.mfa_enabled:
        # Create MFA_PENDING session (cannot access protected resources)
        raw_token, session_record = create_session(
            db=db,
            user_id=user.id,
            state=SessionState.MFA_PENDING
        )
        log_audit_event(
            db=db,
            event_type="login_password_success_mfa_pending",
            outcome="success",
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent
        )
        return raw_token, session_record, "mfa_pending", user
    else:
        # MFA not enabled: create fully AUTHENTICATED session
        raw_token, session_record = create_session(
            db=db,
            user_id=user.id,
            state=SessionState.AUTHENTICATED
        )
        log_audit_event(
            db=db,
            event_type="login_success",
            outcome="success",
            user_id=user.id,
            email=normalized_email,
            ip=ip,
            user_agent=user_agent
        )
        return raw_token, session_record, "authenticated", user
