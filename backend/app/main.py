from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.errors import (
    NexisAPIException,
    nexis_api_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.modules.auth.router import router as auth_router
from app.modules.mfa.router import router as mfa_router
from app.modules.recovery.router import router as recovery_router


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces essential HTTP security headers across all responses (NFR4)."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "frame-ancestors 'none';"
        )
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app = FastAPI(
    title="Nexis MFA API",
    description="Multi-Factor Authentication API designed for accessibility and security compliance (WCAG 2.1 AA, NIST SP 800-63B, OWASP, RFC 6238).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Exception handlers
app.add_exception_handler(NexisAPIException, nexis_api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Retry-After"]
)

# Include module routers
app.include_router(auth_router)
app.include_router(mfa_router)
app.include_router(recovery_router)


@app.get("/api/health", tags=["Health"], summary="API health check through proxy")
@app.get("/health", tags=["Health"], summary="System health check")
def health():
    """Health check endpoint for Docker Compose and monitoring."""
    return {"status": "ok", "service": "nexis-auth-backend"}
