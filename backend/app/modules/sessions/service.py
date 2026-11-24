from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
import uuid
from sqlalchemy.orm import Session
from app.db.models import SessionModel, SessionState, User
from app.core.config import settings
from app.core.security import generate_session_token, hash_token
from app.core.errors import SessionExpiredException

def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Helper to ensure datetime is timezone-aware across both PostgreSQL and SQLite."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def create_session(
    db: Session,
    user_id: uuid.UUID,
    state: SessionState = SessionState.AUTHENTICATED
) -> Tuple[str, SessionModel]:
    """
    Create a new server-side session (FR8, A10, A40).
    Returns (raw_token, session_model).
    """
    raw_token, token_hash = generate_session_token()
    now = datetime.now(timezone.utc)

    if state == SessionState.MFA_PENDING:
        # MFA pending sessions are short-lived (5 minutes)
        idle_expiry = now + timedelta(minutes=settings.pending_mfa_minutes)
        absolute_expiry = now + timedelta(minutes=settings.pending_mfa_minutes)
    else:
        idle_expiry = now + timedelta(minutes=settings.session_idle_minutes)
        absolute_expiry = now + timedelta(hours=settings.session_absolute_hours)

    session_record = SessionModel(
        id=token_hash,
        user_id=user_id,
        state=state,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=idle_expiry,
        absolute_expires_at=absolute_expiry,
        revoked_at=None
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return raw_token, session_record


def validate_and_refresh_session(
    db: Session,
    raw_token: str
) -> Optional[SessionModel]:
    """
    Validate session token and refresh idle expiry if active (FR8, A40).
    Rejects expired and revoked sessions.
    """
    if not raw_token:
        return None

    token_hash = hash_token(raw_token)
    session_record = db.query(SessionModel).filter(SessionModel.id == token_hash).first()

    if not session_record:
        return None

    if session_record.state == SessionState.REVOKED:
        return None

    now = datetime.now(timezone.utc)

    # Check absolute expiry (A40)
    if now > _to_utc(session_record.absolute_expires_at):
        session_record.state = SessionState.REVOKED
        session_record.revoked_at = now
        db.commit()
        return None

    # Check idle expiry (A40)
    if now > _to_utc(session_record.idle_expires_at):
        session_record.state = SessionState.REVOKED
        session_record.revoked_at = now
        db.commit()
        return None

    # Update last_seen_at and roll idle_expires_at forward
    session_record.last_seen_at = now
    if session_record.state == SessionState.MFA_PENDING:
        session_record.idle_expires_at = now + timedelta(minutes=settings.pending_mfa_minutes)
    else:
        session_record.idle_expires_at = now + timedelta(minutes=settings.session_idle_minutes)

    db.commit()
    return session_record


def rotate_session(
    db: Session,
    old_token_hash: str,
    user_id: uuid.UUID,
    new_state: SessionState = SessionState.AUTHENTICATED
) -> Tuple[str, SessionModel]:
    """
    Rotate session on privilege escalation (password -> full auth) (FR8).
    Atomically revokes the old session and creates a fresh session.
    """
    now = datetime.now(timezone.utc)
    old_session = db.query(SessionModel).filter(SessionModel.id == old_token_hash).first()
    if old_session:
        old_session.state = SessionState.REVOKED
        old_session.revoked_at = now

    raw_token, new_session = create_session(db, user_id=user_id, state=new_state)
    return raw_token, new_session


def revoke_session(db: Session, raw_token: str) -> bool:
    """Revoke a single session by token (FR8)."""
    token_hash = hash_token(raw_token)
    session_record = db.query(SessionModel).filter(SessionModel.id == token_hash).first()
    if session_record and session_record.state != SessionState.REVOKED:
        session_record.state = SessionState.REVOKED
        session_record.revoked_at = datetime.now(timezone.utc)
        db.commit()
        return True
    return False


def revoke_all_user_sessions(db: Session, user_id: uuid.UUID) -> int:
    """Revoke all active sessions for a user (used after recovery/password change) (FR8)."""
    now = datetime.now(timezone.utc)
    updated = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.state != SessionState.REVOKED
    ).update({
        "state": SessionState.REVOKED,
        "revoked_at": now
    })
    db.commit()
    return updated
