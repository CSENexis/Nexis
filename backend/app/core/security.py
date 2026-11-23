import os
import secrets
import hashlib
import hmac
from typing import Optional, Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash
from cryptography.fernet import Fernet
from app.core.config import settings

# Argon2id hasher with OWASP recommended parameters
# Memory: 64 MiB (65536 KiB), Time: 3 iterations, Parallelism: 4 threads
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)

# Static dummy hash for timing equalization when user is not found (FR1, FR11)
DUMMY_ARGON2_HASH = ph.hash("nexis_dummy_timing_equalizer_password_string")

# Common passwords blocklist to reject weak passwords (NIST SP 800-63B, A39)
COMMON_PASSWORDS = {
    "password", "password123", "12345678", "123456789", "qwerty123",
    "admin123", "welcome1", "letmein123", "iloveyou", "monkey123",
    "dragon12", "sunshine", "princess", "football", "trustno1"
}


def hash_password(password: str) -> str:
    """Hash password using Argon2id with OWASP parameters (A8, NFR3)."""
    return ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against Argon2id hash with timing protection."""
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def dummy_verify_password(password: str) -> bool:
    """Run dummy Argon2id verification to equalize timing for non-existent users (FR1, FR11)."""
    try:
        ph.verify(DUMMY_ARGON2_HASH, password)
    except Exception:
        pass
    return False


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength according to NIST SP 800-63B (A39):
    - Minimum 8 characters
    - Maximum 128 characters
    - Allow spaces and passphrases
    - Reject common passwords
    - No arbitrary composition rules (no mandatory special characters)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    if password.lower() in COMMON_PASSWORDS:
        return False, "Password is too common and easily guessable. Please choose a more unique passphrase."
    return True, None


def generate_session_token() -> Tuple[str, str]:
    """
    Generate a cryptographically secure 256-bit random session token (FR8, A10).
    Returns:
        (raw_token, token_hash)
        raw_token: sent to client in HttpOnly cookie
        token_hash: stored in PostgreSQL sessions.id column
    """
    raw_token = secrets.token_urlsafe(32)  # 256 bits of entropy
    token_hash = hash_token(raw_token)
    return raw_token, token_hash


def hash_token(token: str) -> str:
    """Hash token using SHA-256 for secure database storage (NFR3)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_identifier(identifier: str) -> str:
    """Hash email/identifier for safe Redis key scoping and audit logs without leaks (NFR3, A43)."""
    normalized = identifier.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# Fernet symmetric encryption for TOTP secrets at rest (FR3, A41)
def get_fernet() -> Fernet:
    """Derive Fernet cipher from TOTP_ENC_KEY."""
    key = settings.totp_enc_key.encode("utf-8")
    return Fernet(key)


def encrypt_totp_secret(secret_base32: str) -> str:
    """Encrypt TOTP base32 secret before writing to database (A41)."""
    cipher = get_fernet()
    return cipher.encrypt(secret_base32.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """Decrypt TOTP base32 secret retrieved from database."""
    cipher = get_fernet()
    return cipher.decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")


# Recovery codes generation and hashing (FR6, FR7, A15, A16)
# Unambiguous alphabet omitting 0, O, 1, I, L to maximize accessibility
RECOVERY_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

def generate_single_recovery_code() -> str:
    """Generate a single formatted recovery code: XXXX-XXXX-XXXX (12 chars)."""
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(12))
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def generate_recovery_codes_batch(count: int = 10) -> list[str]:
    """Generate 10 cryptographically secure recovery codes (FR6, A17)."""
    return [generate_single_recovery_code() for _ in range(count)]


def normalize_recovery_code(code: str) -> str:
    """Normalize recovery code by stripping spaces, hyphens, and uppercasing."""
    return code.replace("-", "").replace(" ", "").strip().upper()


def hash_recovery_code(code: str) -> str:
    """
    Hash recovery code with HMAC-SHA256 using HMAC_KEY (FR7, A16).
    Only hashes are stored in the database.
    """
    normalized = normalize_recovery_code(code)
    return hmac.new(
        settings.hmac_key.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
