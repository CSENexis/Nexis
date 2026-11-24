import uuid
from app.db.models import AuditLog
from app.modules.security.audit import log_audit_event

def test_audit_log_credential_confidentiality(db_session):
    user_id = uuid.uuid4()
    raw_email = "alice@example.com"

    # Attempt to log with sensitive fields in details
    sensitive_details = {
        "password": "super_secret_password",
        "totp_code": "123456",
        "recovery_code": "XXXX-YYYY-ZZZZ",
        "safe_browser": "Chrome",
        "nested": {
            "token": "raw_secret_token",
            "attempt_number": 2
        }
    }

    log_entry = log_audit_event(
        db=db_session,
        event_type="test_event",
        outcome="failure",
        user_id=user_id,
        email=raw_email,
        ip="127.0.0.1",
        user_agent="pytest-client",
        details=sensitive_details
    )

    assert log_entry.id is not None
    # Email must be hashed, never plaintext
    assert log_entry.email_hash is not None
    assert raw_email not in log_entry.email_hash

    # Sensitive values in details must be strictly redacted
    details = log_entry.details
    assert details["password"] == "[REDACTED]"
    assert details["totp_code"] == "[REDACTED]"
    assert details["recovery_code"] == "[REDACTED]"
    assert details["safe_browser"] == "Chrome"
    assert details["nested"]["token"] == "[REDACTED]"
    assert details["nested"]["attempt_number"] == 2
