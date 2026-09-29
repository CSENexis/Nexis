import pytest

from app.security.passwords import (
    hash_password,
    password_needs_rehash,
    verify_password,
)


# These are test-only values, not real account credentials.
TEST_PASSWORD = "Nexis-test-password!"


def test_password_is_an_argon2id_hash():
    password_hash = hash_password(TEST_PASSWORD)

    assert password_hash != TEST_PASSWORD
    assert password_hash.startswith("$argon2id$")


def test_correct_password_succeeds():
    password_hash = hash_password(TEST_PASSWORD)

    assert verify_password(TEST_PASSWORD, password_hash) is True


def test_incorrect_password_fails():
    password_hash = hash_password(TEST_PASSWORD)

    assert verify_password("Incorrect-password!", password_hash) is False


def test_each_hash_uses_a_fresh_salt():
    first = hash_password(TEST_PASSWORD)
    second = hash_password(TEST_PASSWORD)

    assert first != second
    assert verify_password(TEST_PASSWORD, first) is True
    assert verify_password(TEST_PASSWORD, second) is True


@pytest.mark.parametrize("password", ["", "short", "1234567"])
def test_short_password_is_rejected(password):
    with pytest.raises(ValueError):
        hash_password(password)


def test_eight_character_password_is_accepted():
    password_hash = hash_password("12345678")

    assert verify_password("12345678", password_hash) is True


def test_invalid_hash_is_rejected():
    assert verify_password(TEST_PASSWORD, "invalid-hash") is False


def test_new_hash_does_not_need_rehashing():
    password_hash = hash_password(TEST_PASSWORD)

    assert password_needs_rehash(password_hash) is False
