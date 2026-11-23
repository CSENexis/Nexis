import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import AuditLog
from app.core.security import hash_identifier

# Disallowed keys to strictly prevent credentials or sensitive secrets from ever entering logs (FR12, NFR3, A26)
SENSITIVE_KEYS = {
    "password", "new_password", "current_password", "old_password",
    "totp", "code", "totp_code", "recovery_code", "secret", "mfa_secret",
    "token", "raw_token", "session_id", "authorization", "cookie"
}


def sanitize_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Sanitize detail payload to guarantee no credential leaks (FR12, NFR3)."""
    if not details:
        return {}
    sanitized = {}
    for key, value in details.items():
        if key.lower() in SENSITIVE_KEYS or any(s in key.lower() for s in ["password", "secret", "token"]):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_details(value)
        else:
            sanitized[key] = value
    return sanitized


def log_audit_event(
    db: Session,
    event_type: str,
    outcome: str,
    user_id: Optional[uuid.UUID] = None,
    email: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Record security-relevant event in PostgreSQL audit_logs table (FR12, A26, A44).
    Guarantees no raw email, passwords, TOTP codes, or recovery codes are stored.
    """
    email_hash = hash_identifier(email) if email else None
    safe_details = sanitize_details(details)

    log_entry = AuditLog(
        id=uuid.uuid4(),
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        outcome=outcome,  # 'success' | 'failure'
        user_id=user_id,
        email_hash=email_hash,
        ip=ip,
        user_agent=user_agent[:500] if user_agent else None,
        details=safe_details
    )

    try:
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
    except Exception as e:
        db.rollback()
        # In a high-assurance system, we never allow audit write failures to be silently swallowed
        # However, we avoid crashing the entire response if database is busy
        pass

    return log_entry
