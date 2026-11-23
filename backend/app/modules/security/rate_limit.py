import redis
from typing import Optional
from redis.exceptions import RedisError
from app.core.errors import RateLimitExceededException, NexisAPIException

def check_rate_limit(
    redis_client: redis.Redis,
    key_prefix: str,
    identifier: str,
    limit: int,
    window_seconds: int = 60
) -> None:
    """
    Enforces Redis-based atomic rate limiting (FR9, A24, NFR6).
    Key pattern: rl:{key_prefix}:{identifier}
    If limit is exceeded, raises RateLimitExceededException with Retry-After header.
    Fails closed if Redis is unavailable.
    """
    redis_key = f"rl:{key_prefix}:{identifier}"
    try:
        pipeline = redis_client.pipeline()
        pipeline.incr(redis_key)
        pipeline.ttl(redis_key)
        count, current_ttl = pipeline.execute()

        # If key was newly created, set its TTL window
        if count == 1 or current_ttl == -1:
            redis_client.expire(redis_key, window_seconds)
            current_ttl = window_seconds

        if count > limit:
            retry_after = max(1, current_ttl)
            raise RateLimitExceededException(retry_after_seconds=retry_after)

    except RedisError as e:
        # Fail closed on dependency failure (NFR6)
        raise NexisAPIException(
            status_code=503,
            code="SERVICE_UNAVAILABLE",
            message="Security rate limiting service is temporarily unavailable. Request denied for safety."
        )
