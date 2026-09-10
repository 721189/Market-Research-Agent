import time
import redis
from backend.app.config import settings
import logging

logger = logging.getLogger("marketai.ratelimit")

class RateLimiter:
    def __init__(self):
        try:
            self.redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed for rate limiting: {e}")
            self.redis = None

    def check_rate_limit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """
        Sliding-window counter rate limit via Redis.
        Returns True if within limit, False if rate exceeded.
        """
        if not self.redis:
            return True # Fail open gracefully if Redis is momentarily unavailable

        try:
            now = time.time()
            clear_before = now - window_seconds
            pipe = self.redis.pipeline()
            redis_key = f"ratelimit:{key}"
            
            pipe.zremrangebyscore(redis_key, 0, clear_before)
            pipe.zadd(redis_key, {str(now): now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window_seconds)
            
            results = pipe.execute()
            count = results[2]
            return count <= limit
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return True

rate_limiter = RateLimiter()
