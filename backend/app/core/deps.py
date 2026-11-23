from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Generator
import redis
from app.core.config import settings
from app.db.session import get_db
from app.db.models import SessionModel, SessionState, User
from app.modules.sessions.service import validate_and_refresh_session
from app.core.errors import (
    SessionExpiredException,
    MfaRequiredException,
    CsrfValidationException,
    NexisAPIException
)

# Global Redis client pool
_redis_pool = None

def get_redis_client() -> redis.Redis:
    """Provides Redis client connection pool (FR9, A24)."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
    return redis.Redis(connection_pool=_redis_pool)


def get_current_session_token(request: Request) -> Optional[str]:
    """Extract session token from HttpOnly cookie (FR8, A10)."""
    return request.cookies.get(settings.cookie_name)


def get_current_session(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[SessionModel]:
    """Retrieve and validate the active session from request cookie (FR8)."""
    raw_token = get_current_session_token(request)
    if not raw_token:
        return None
    session_record = validate_and_refresh_session(db, raw_token)
    return session_record


def require_authenticated(
    request: Request,
    session_record: Optional[SessionModel] = Depends(get_current_session)
) -> SessionModel:
    """
    Dependency that enforces a fully authenticated session (FR2, FR8).
    Rejects missing, expired, revoked, or MFA_PENDING sessions with controlled 401.
    """
    if not session_record:
        raise SessionExpiredException("Authentication required. Please sign in.")

    if session_record.state == SessionState.MFA_PENDING:
        # MFA pending session must not access any protected resource (FR2)
        raise MfaRequiredException("Multi-factor authentication required. Please verify your one-time code.")

    if session_record.state == SessionState.REVOKED:
        raise SessionExpiredException("Your session has been revoked. Please sign in again.")

    return session_record


def require_mfa_pending(
    request: Request,
    session_record: Optional[SessionModel] = Depends(get_current_session)
) -> SessionModel:
    """
    Dependency for TOTP verification endpoint.
    Requires session to be in MFA_PENDING state.
    """
    if not session_record:
        raise SessionExpiredException("Your verification session has expired. Please sign in again.")

    if session_record.state != SessionState.MFA_PENDING:
        if session_record.state == SessionState.AUTHENTICATED:
            # Already authenticated
            return session_record
        raise SessionExpiredException("Invalid session state for MFA verification. Please sign in again.")

    return session_record


def verify_csrf(request: Request) -> None:
    """
    CSRF protection for state-changing requests using cookie sessions (FR8).
    Enforces custom header 'X-Requested-With' or 'X-CSRF-Token'.
    """
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        requested_with = request.headers.get("x-requested-with")
        csrf_token = request.headers.get("x-csrf-token")
        # In modern SPA architectures, requiring a custom header prevents simple cross-origin form submits
        if not requested_with and not csrf_token:
            # For browser form submissions or cross-origin requests lacking custom headers
            raise CsrfValidationException("Missing required CSRF security header (X-Requested-With or X-CSRF-Token).")


def get_client_ip(request: Request) -> str:
    """Extract client IP address handling proxies safely."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First entry is client IP
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def get_client_user_agent(request: Request) -> str:
    """Extract User-Agent string."""
    return request.headers.get("user-agent", "")[:500]
