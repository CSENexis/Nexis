import pytest
from app.modules.security.rate_limit import check_rate_limit
from app.modules.security.lockout import (
    check_lockout,
    record_failed_attempt,
    reset_lockout
)
from app.core.errors import RateLimitExceededException, AccountLockedException

def test_rate_limiting(fake_redis):
    key_prefix = "test_endpoint"
    identifier = "127.0.0.1"

    # Allow 3 requests
    check_rate_limit(fake_redis, key_prefix, identifier, limit=3, window_seconds=60)
    check_rate_limit(fake_redis, key_prefix, identifier, limit=3, window_seconds=60)
    check_rate_limit(fake_redis, key_prefix, identifier, limit=3, window_seconds=60)

    # 4th request must trigger RateLimitExceededException
    with pytest.raises(RateLimitExceededException) as exc_info:
        check_rate_limit(fake_redis, key_prefix, identifier, limit=3, window_seconds=60)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


def test_lockout_trigger_and_reset(fake_redis):
    account_hash = "hashed_user_email"
    ip = "192.168.1.100"

    # 4 consecutive failures: not locked yet
    for _ in range(4):
        _, locked_ttl = record_failed_attempt(fake_redis, account_hash, ip)
        assert locked_ttl is None

    # 5th failure: triggers lockout
    count, locked_ttl = record_failed_attempt(fake_redis, account_hash, ip)
    assert count == 5
    assert locked_ttl is not None
    assert locked_ttl > 0

    # check_lockout now raises AccountLockedException
    with pytest.raises(AccountLockedException) as exc_info:
        check_lockout(fake_redis, account_hash, ip)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
    assert "Account temporarily locked" in exc_info.value.message

    # Resetting clears lockout
    reset_lockout(fake_redis, account_hash, ip)
    # Should not raise now
    check_lockout(fake_redis, account_hash, ip)
