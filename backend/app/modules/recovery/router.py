from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
import redis

from app.db.session import get_db
from app.db.models import User, SessionModel
from app.core.deps import (
    get_redis_client,
    require_authenticated,
    verify_csrf,
    get_client_ip,
    get_client_user_agent
)
from app.core.errors import NexisAPIException
from app.modules.recovery.schemas import (
    RecoveryStartRequest,
    RecoveryStartResponse,
    RecoveryCompleteRequest,
    RecoveryCompleteResponse,
    RecoveryRegenerateResponse
)
from app.modules.recovery.service import (
    start_account_recovery,
    complete_account_recovery,
    regenerate_user_recovery_codes
)

router = APIRouter(prefix="/api/recovery", tags=["Account Recovery"])


@router.post(
    "/start",
    response_model=RecoveryStartResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Initiate account recovery using a one-time recovery code"
)
def recovery_start(
    req: RecoveryStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Validate recovery code against stored hashes and issue short-lived recovery token (FR7, A18).
    Code is consumed atomically. Generic error prevents account enumeration (FR11).
    """
    ip = get_client_ip(request)
    ua = get_client_user_agent(request)

    recovery_token = start_account_recovery(
        db=db,
        redis_client=redis_client,
        email=req.email,
        recovery_code=req.recovery_code,
        ip=ip,
        user_agent=ua
    )

    return RecoveryStartResponse(
        message="Recovery code verified successfully. Please choose a new password.",
        recovery_token=recovery_token
    )


@router.post(
    "/complete",
    response_model=RecoveryCompleteResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Complete recovery: set new password and reset MFA"
)
def recovery_complete(
    req: RecoveryCompleteRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Set new password, reset MFA secret, and revoke all active sessions (FR7, A19).
    User will re-enrol MFA on next sign-in.
    """
    ip = get_client_ip(request)
    ua = get_client_user_agent(request)

    complete_account_recovery(
        db=db,
        recovery_token=req.recovery_token,
        new_password=req.new_password,
        ip=ip,
        user_agent=ua
    )

    return RecoveryCompleteResponse(
        message="Password updated successfully and multi-factor authentication reset. Please sign in with your new password to set up MFA."
    )


@router.post(
    "/regenerate",
    response_model=RecoveryRegenerateResponse,
    dependencies=[Depends(verify_csrf)],
    summary="Regenerate recovery codes for authenticated user"
)
def recovery_regenerate(
    request: Request,
    session: SessionModel = Depends(require_authenticated),
    db: Session = Depends(get_db)
):
    """Regenerate 10 recovery codes, invalidating prior unused codes (FR6)."""
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise NexisAPIException(status_code=404, code="USER_NOT_FOUND", message="User not found.")

    ip = get_client_ip(request)
    ua = get_client_user_agent(request)

    new_codes = regenerate_user_recovery_codes(
        db=db,
        user=user,
        ip=ip,
        user_agent=ua
    )

    return RecoveryRegenerateResponse(
        message="New recovery codes generated. All previous recovery codes have been invalidated.",
        recovery_codes=new_codes
    )
