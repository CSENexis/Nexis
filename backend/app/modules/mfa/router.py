from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session
import redis

from app.db.session import get_db
from app.db.models import User, SessionModel
from app.core.config import settings
from app.core.deps import (
    get_redis_client,
    require_authenticated,
    require_mfa_pending,
    verify_csrf,
    get_client_ip,
    get_client_user_agent
)
from app.core.errors import NexisAPIException
from app.modules.auth.router import set_session_cookie
from app.modules.mfa.schemas import (
    MfaEnrolStartResponse,
    MfaEnrolConfirmRequest,
    MfaEnrolConfirmResponse,
    MfaVerifyRequest,
    MfaVerifyResponse
)
from app.modules.mfa.service import (
    start_mfa_enrolment,
    confirm_mfa_enrolment,
    verify_totp_code
)

router = APIRouter(prefix="/api/mfa", tags=["Multi-Factor Authentication"])


@router.post(
    "/enrol/start",
    response_model=MfaEnrolStartResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Begin MFA enrolment (Text secret first + optional QR)"
)
def enrol_start(
    request: Request,
    session: SessionModel = Depends(require_authenticated),
    db: Session = Depends(get_db)
):
    """
    Generate TOTP secret and present text secret first with optional QR code (FR3, A14).
    Accessible to screen-reader users with grouped text chunks.
    """
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise NexisAPIException(status_code=404, code="USER_NOT_FOUND", message="User not found.")

    if user.mfa_enabled:
        raise NexisAPIException(status_code=400, code="MFA_ALREADY_ENABLED", message="MFA is already enabled on this account.")

    ip = get_client_ip(request)
    ua = get_client_user_agent(request)

    raw_secret, grouped_secret, otpauth_uri, qr_data_uri = start_mfa_enrolment(
        db=db,
        user=user,
        ip=ip,
        user_agent=ua
    )

    return MfaEnrolStartResponse(
        secret=raw_secret,
        secret_grouped=grouped_secret,
        otpauth_uri=otpauth_uri,
        qr_code_data_uri=qr_data_uri,
        message="MFA setup secret generated. You can enter the text key manually into your authenticator app or optionally scan the QR code."
    )


@router.post(
    "/enrol/confirm",
    response_model=MfaEnrolConfirmResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Confirm MFA enrolment and generate recovery codes"
)
def enrol_confirm(
    req: MfaEnrolConfirmRequest,
    request: Request,
    session: SessionModel = Depends(require_authenticated),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Verify 6-digit code against pending secret before activating MFA (FR4).
    Returns 10 single-use recovery codes upon successful confirmation (FR6).
    """
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise NexisAPIException(status_code=404, code="USER_NOT_FOUND", message="User not found.")

    ip = get_client_ip(request)
    ua = get_client_user_agent(request)

    recovery_codes = confirm_mfa_enrolment(
        db=db,
        redis_client=redis_client,
        user=user,
        submitted_code=req.code,
        ip=ip,
        user_agent=ua
    )

    return MfaEnrolConfirmResponse(
        message="Multi-factor authentication enabled successfully. Please securely save your one-time recovery codes.",
        recovery_codes=recovery_codes
    )


@router.post(
    "/verify",
    response_model=MfaVerifyResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Verify TOTP code during sign-in"
)
def verify(
    req: MfaVerifyRequest,
    request: Request,
    response: Response,
    session: SessionModel = Depends(require_mfa_pending),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Verify 6-digit TOTP code (FR5).
    Replay prevention is enforced atomically (NFR5, A42).
    On success, elevates session to AUTHENTICATED with token rotation.
    """
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise NexisAPIException(status_code=404, code="USER_NOT_FOUND", message="User not found.")

    ip = get_client_ip(request)
    ua = get_client_user_agent(request)

    new_raw_token, _ = verify_totp_code(
        db=db,
        redis_client=redis_client,
        user=user,
        session_record=session,
        submitted_code=req.code,
        ip=ip,
        user_agent=ua
    )

    set_session_cookie(response, new_raw_token)

    return MfaVerifyResponse(
        status="authenticated",
        message="Verification successful. Access granted."
    )
