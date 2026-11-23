from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session
import redis

from app.db.session import get_db
from app.db.models import User, SessionModel, SessionState
from app.core.config import settings
from app.core.deps import (
    get_redis_client,
    get_current_session,
    get_current_session_token,
    verify_csrf,
    get_client_ip,
    get_client_user_agent
)
from app.modules.auth.schemas import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    LoginResponse,
    AuthMeResponse,
    MessageResponse
)
from app.modules.auth.service import register_user, authenticate_user
from app.modules.sessions.service import revoke_session
from app.modules.security.audit import log_audit_event

router = APIRouter(prefix="/api/auth", tags=["Core Authentication"])


def set_session_cookie(response: Response, raw_token: str) -> None:
    """Set secure HttpOnly session cookie (FR8, NFR4, A10, A27)."""
    response.set_cookie(
        key=settings.cookie_name,
        value=raw_token,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=settings.cookie_path,
        max_age=settings.session_absolute_hours * 3600
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie on logout or session revocation."""
    response.delete_cookie(
        key=settings.cookie_name,
        path=settings.cookie_path,
        httponly=settings.cookie_httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Register a new user account"
)
def register(
    req: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Register a new user with email and password (FR1, A39).
    Generic response prevents account enumeration (FR11).
    """
    ip = get_client_ip(request)
    ua = get_client_user_agent(request)
    _, msg = register_user(
        db=db,
        redis_client=redis_client,
        email=req.email,
        password=req.password,
        ip=ip,
        user_agent=ua
    )
    return RegisterResponse(message=msg)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Authenticate with email and password"
)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Verify password using Argon2id with dummy timing equalization (FR1, FR2, FR8).
    Creates an AUTHENTICATED or MFA_PENDING session and sets an HttpOnly cookie.
    """
    ip = get_client_ip(request)
    ua = get_client_user_agent(request)
    raw_token, session_record, auth_status, user = authenticate_user(
        db=db,
        redis_client=redis_client,
        email=req.email,
        password=req.password,
        ip=ip,
        user_agent=ua
    )

    set_session_cookie(response, raw_token)

    if auth_status == "mfa_pending":
        message = "Password verified. Please enter the 6-digit code from your authenticator app."
    else:
        message = "Authentication successful. Welcome to your account."

    return LoginResponse(
        status=auth_status,
        message=message,
        email=user.email,
        mfa_enabled=user.mfa_enabled
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Revoke the active session"
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Revoke session immediately and clear the session cookie (FR8)."""
    raw_token = get_current_session_token(request)
    ip = get_client_ip(request)
    ua = get_client_user_agent(request)

    if raw_token:
        revoke_session(db, raw_token)
        log_audit_event(
            db=db,
            event_type="logout",
            outcome="success",
            ip=ip,
            user_agent=ua
        )

    clear_session_cookie(response)
    return MessageResponse(message="Signed out successfully.")


@router.get(
    "/me",
    response_model=AuthMeResponse,
    summary="Get current user authentication and MFA status"
)
def me(
    session_record: Optional[SessionModel] = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """
    Inspects active session. Backend session is the single source of truth (A36).
    Returns enough state for frontend routing (unauthenticated, mfa_pending, authenticated).
    """
    if not session_record or session_record.state == SessionState.REVOKED:
        return AuthMeResponse(
            status="unauthenticated",
            user_id=None,
            email=None,
            mfa_enabled=False
        )

    user = db.query(User).filter(User.id == session_record.user_id).first()
    if not user:
        return AuthMeResponse(
            status="unauthenticated",
            user_id=None,
            email=None,
            mfa_enabled=False
        )

    if session_record.state == SessionState.MFA_PENDING:
        return AuthMeResponse(
            status="mfa_pending",
            user_id=str(user.id),
            email=user.email,
            mfa_enabled=user.mfa_enabled
        )

    return AuthMeResponse(
        status="authenticated",
        user_id=str(user.id),
        email=user.email,
        mfa_enabled=user.mfa_enabled
    )
