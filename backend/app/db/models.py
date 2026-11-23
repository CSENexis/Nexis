import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Text,
    BigInteger,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
    func
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base

# Universal UUID type that works in both PostgreSQL and SQLite
try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID_TYPE
    UUID_TYPE = PG_UUID_TYPE(as_uuid=True)
except Exception:
    UUID_TYPE = String(36)


class SessionState(str, enum.Enum):
    MFA_PENDING = "MFA_PENDING"
    AUTHENTICATED = "AUTHENTICATED"
    REVOKED = "REVOKED"


class User(Base):
    """
    Users table - Section 4
    FR1, FR2, FR5, A8, A39, A41, A42
    """
    __tablename__ = "users"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret_encrypted = Column(Text, nullable=True)
    mfa_pending_secret_encrypted = Column(Text, nullable=True)
    last_totp_step = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    recovery_codes = relationship("RecoveryCode", back_populates="user", cascade="all, delete-orphan")
    recovery_tokens = relationship("RecoveryToken", back_populates="user", cascade="all, delete-orphan")


class SessionModel(Base):
    """
    Sessions table - Section 4
    FR8, A10, A40
    Note: 'id' stores the SHA-256 hash of the random 256-bit bearer token.
    """
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True)  # SHA-256 hash of the raw token
    user_id = Column(UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    state = Column(
        SQLEnum(SessionState, name="session_state_enum", native_enum=False),
        nullable=False,
        default=SessionState.MFA_PENDING
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    idle_expires_at = Column(DateTime(timezone=True), nullable=False)
    absolute_expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")


class RecoveryCode(Base):
    """
    Recovery codes table - Section 4
    FR6, FR7, NFR5, A15-A18
    Note: 'code_hash' stores SHA-256 hash of the normalized recovery code.
    """
    __tablename__ = "recovery_codes"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="recovery_codes")


class RecoveryToken(Base):
    """
    Recovery tokens table - Section 4
    FR7, NFR5
    Issued after a recovery code is consumed; scoped to 'set new password + re-enrol MFA'.
    """
    __tablename__ = "recovery_tokens"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID_TYPE, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="recovery_tokens")


class AuditLog(Base):
    """
    Audit logs table - Section 4
    FR12, A26, A44
    Never logs passwords, TOTP codes, recovery codes, secrets, or raw session ids.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    outcome = Column(String(16), nullable=False)  # 'success' | 'failure'
    user_id = Column(UUID_TYPE, nullable=True, index=True)
    email_hash = Column(String(128), nullable=True, index=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    details = Column(JSON, nullable=True)
