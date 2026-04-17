import redis

from .config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL)


def _key(scope: str, identifier: str) -> str:
    return f"ratelimit:{scope}:{identifier}"


def check_rate_limit(scope: str, identifier: str, max_attempts: int, window_seconds: int) -> bool:
    """
    Return True when request is allowed, False when blocked.
    """
    key = _key(scope, identifier)
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window_seconds)
    return count <= max_attempts
