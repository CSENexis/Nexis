import redis
from typing import Tuple, Optional
from redis.exceptions import RedisError
from app.core.config import settings
from app.core.errors import AccountLockedException, NexisAPIException

def get_lockout_keys(account_hash: str, ip: str) -> Tuple[str, str]:
    """Generate scoped Redis keys for failure counter and active lockout."""
    # Scoped per account + IP to protect against brute force while mitigating DoS on shared IPs
    fail_counter_key = f"lockout:fail_count:{account_hash}:{ip}"
    lockout_active_key = f"lockout:active:{account_hash}:{ip}"
    return fail_counter_key, lockout_active_key


def check_lockout(
    redis_client: redis.Redis,
    account_hash: str,
    ip: str
) -> None:
    """
    Check if the account/IP combination is currently locked out (FR9, A25).
    Raises AccountLockedException with Retry-After if locked.
    Fails closed if Redis is unreachable (NFR6).
    """
    _, lockout_active_key = get_lockout_keys(account_hash, ip)
    try:
        ttl = redis_client.ttl(lockout_active_key)
        if ttl > 0:
            raise AccountLockedException(retry_after_seconds=ttl)
    except RedisError:
        raise NexisAPIException(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="Security lockout service is temporarily unavailable. Request denied for safety."
        )


def record_failed_attempt(
    redis_client: redis.Redis,
    account_hash: str,
    ip: str
) -> Tuple[int, Optional[int]]:
    """
    Record a failed authentication attempt (FR9, A25).
    Increments failure counter. If threshold reached, triggers lockout.
    Returns:
        (consecutive_failures, lockout_ttl_seconds_or_none)
    """
    fail_counter_key, lockout_active_key = get_lockout_keys(account_hash, ip)
    window_seconds = settings.lockout_duration_minutes * 60

    try:
        pipeline = redis_client.pipeline()
        pipeline.incr(fail_counter_key)
        pipeline.ttl(fail_counter_key)
        count, current_ttl = pipeline.execute()

        if count == 1 or current_ttl == -1:
            redis_client.expire(fail_counter_key, window_seconds)

        if count >= settings.lockout_threshold:
            # Trigger temporary lockout
            redis_client.set(lockout_active_key, "locked", ex=window_seconds)
            return count, window_seconds

        return count, None
    except RedisError:
        raise NexisAPIException(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="Security service is temporarily unavailable. Request denied for safety."
        )


def reset_lockout(
    redis_client: redis.Redis,
    account_hash: str,
    ip: str
) -> None:
    """Clear failed attempts and lockout state on successful authentication."""
    fail_counter_key, lockout_active_key = get_lockout_keys(account_hash, ip)
    try:
        redis_client.delete(fail_counter_key, lockout_active_key)
    except RedisError:
        pass
