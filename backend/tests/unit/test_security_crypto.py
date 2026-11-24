import pytest
from app.core.security import (
    hash_password,
    verify_password,
    dummy_verify_password,
    validate_password_strength,
    encrypt_totp_secret,
    decrypt_totp_secret,
    generate_single_recovery_code,
    generate_recovery_codes_batch,
    hash_recovery_code,
    normalize_recovery_code,
    RECOVERY_ALPHABET
)

def test_argon2id_password_hashing():
    password = "CorrectHorseBatteryStaple!"
    hashed = hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False


def test_dummy_verify_password():
    # Should safely return False and not raise
    assert dummy_verify_password("AnyPasswordAttempt") is False


def test_password_strength_validation():
    # Less than 8 chars
    valid, msg = validate_password_strength("short")
    assert not valid
    assert "at least 8 characters" in msg

    # Common password
    valid, msg = validate_password_strength("password123")
    assert not valid
    assert "too common" in msg

    # Valid passphrase
    valid, msg = validate_password_strength("my-secret-coffee-mug-2026")
    assert valid
    assert msg is None


def test_fernet_totp_encryption():
    secret = "JBSWY3DPEHPK3PXP"
    encrypted = encrypt_totp_secret(secret)

    assert encrypted != secret
    assert isinstance(encrypted, str)

    decrypted = decrypt_totp_secret(encrypted)
    assert decrypted == secret


def test_recovery_code_generation_and_hashing():
    codes = generate_recovery_codes_batch(10)
    assert len(codes) == 10
    assert len(set(codes)) == 10  # All unique

    for code in codes:
        assert len(code) == 14  # XXXX-XXXX-XXXX
        parts = code.split("-")
        assert len(parts) == 3
        for part in parts:
            assert len(part) == 4
            for char in part:
                assert char in RECOVERY_ALPHABET
                # Verify no confusing characters (0, O, 1, I, L)
                assert char not in ["0", "O", "1", "I", "L"]

    # Hashing
    single_code = codes[0]
    hashed1 = hash_recovery_code(single_code)
    hashed2 = hash_recovery_code(single_code.lower().replace("-", " "))
    assert hashed1 == hashed2  # Case and space insensitive
    assert len(hashed1) == 64
