from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Any, Dict, Optional

class NexisAPIException(HTTPException):
    """Base exception returning accessible, structured error response (A31, NFR6, FR10)."""
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.message = message


class AuthenticationFailedException(NexisAPIException):
    def __init__(self, message: str = "Invalid email or password. Please check your credentials and try again."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_FAILED",
            message=message
        )


class AccountLockedException(NexisAPIException):
    def __init__(self, retry_after_seconds: int):
        minutes = max(1, (retry_after_seconds + 59) // 60)
        message = (
            f"Account temporarily locked due to multiple consecutive failed attempts. "
            f"Please wait approximately {minutes} minute(s) before trying again."
        )
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="ACCOUNT_LOCKED",
            message=message,
            headers={"Retry-After": str(retry_after_seconds)}
        )


class RateLimitExceededException(NexisAPIException):
    def __init__(self, retry_after_seconds: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests in a short time. Please slow down and try again shortly.",
            headers={"Retry-After": str(retry_after_seconds)}
        )


class SessionExpiredException(NexisAPIException):
    def __init__(self, message: str = "Your session has expired. Please sign in again."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="SESSION_EXPIRED",
            message=message
        )


class MfaRequiredException(NexisAPIException):
    def __init__(self, message: str = "Multi-factor authentication required. Please enter your 6-digit code."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="MFA_REQUIRED",
            message=message
        )


class MfaInvalidCodeException(NexisAPIException):
    def __init__(self, message: str = "Invalid or expired one-time code. Please check your authenticator app and try again."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MFA_INVALID_CODE",
            message=message
        )


class RecoveryFailedException(NexisAPIException):
    def __init__(self, message: str = "Invalid account identifier or recovery code. Please check your input and try again."):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="RECOVERY_FAILED",
            message=message
        )


class CsrfValidationException(NexisAPIException):
    def __init__(self, message: str = "Cross-Site Request Forgery validation failed. Request rejected."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="CSRF_FAILED",
            message=message
        )


def format_error_response(code: str, message: str) -> Dict[str, Any]:
    """Consistent error payload: { 'error': { 'code': '...', 'message': '...' } }"""
    return {
        "error": {
            "code": code,
            "message": message
        }
    }


async def nexis_api_exception_handler(request: Request, exc: NexisAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(exc.code, exc.message),
        headers=exc.headers
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Accessible error messages for schema validation failures."""
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid input format.") if errors else "Invalid request data."
    loc = errors[0].get("loc", []) if errors else []
    field_name = str(loc[-1]) if loc else "field"
    accessible_message = f"Validation error on {field_name}: {first_msg}"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=format_error_response("VALIDATION_ERROR", accessible_message)
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Fail-closed non-leaky generic error handler (NFR6)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=format_error_response(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred while processing your request. Please try again later."
        )
    )
