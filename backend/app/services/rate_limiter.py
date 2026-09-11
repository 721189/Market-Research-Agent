import time
import logging
import threading
from typing import Tuple, Dict, Any, List
from collections import defaultdict
try:
    import redis
    from redis.exceptions import RedisError, ConnectionError, TimeoutError
except ImportError:
    redis = None # type: ignore
    class RedisError(Exception): pass # type: ignore
    class ConnectionError(Exception): pass # type: ignore
    class TimeoutError(Exception): pass # type: ignore
from backend.app.config import settings

logger = logging.getLogger("marketai.ratelimit")

class RateLimiter:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis: redis.Redis = None
        self._init_redis()

        # Circuit breaker state
        self._circuit_open = False
        self._circuit_open_until = 0.0
        self._consecutive_failures = 0
        self._failure_threshold = 3
        self._cooldown_seconds = 30.0

        # Tier 2: Thread-safe in-memory fallback
        self._local_lock = threading.Lock()
        self._local_store: Dict[str, List[float]] = defaultdict(list)
        self._max_local_keys = 10000

    def _init_redis(self):
        try:
            self.redis = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=1.5,
                socket_connect_timeout=1.5
            )
        except Exception as e:
            logger.warning(f"Initial Redis connection failed: {e}")
            self.redis = None

    def _is_circuit_active(self) -> bool:
        if not self._circuit_open:
            return False
        now = time.time()
        if now >= self._circuit_open_until:
            # Half-open state: attempt single probe
            try:
                if self.redis and self.redis.ping():
                    logger.info("Redis recovered: closing rate-limiter circuit breaker.")
                    self._circuit_open = False
                    self._consecutive_failures = 0
                    return False
            except Exception:
                pass
            # Reset cooldown if probe failed
            self._circuit_open_until = now + self._cooldown_seconds
            return True
        return True

    def _record_failure(self, exc: Exception):
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold and not self._circuit_open:
            logger.warning(
                f"Redis rate limiter tripped circuit breaker after {self._consecutive_failures} failures ({exc}). "
                f"Engaging local in-memory fallback for {self._cooldown_seconds}s."
            )
            self._circuit_open = True
            self._circuit_open_until = time.time() + self._cooldown_seconds

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> bool:
        """
        Dual-tier rate limit check.
        Uses Redis sliding window when healthy, fails over to thread-safe in-memory tier.
        """
        now = time.time()

        # Try Tier 1: Redis
        if self.redis and not self._is_circuit_active():
            try:
                redis_key = f"ratelimit:{key}"
                clear_before = now - window_seconds
                pipe = self.redis.pipeline()
                pipe.zremrangebyscore(redis_key, 0, clear_before)
                pipe.zadd(redis_key, {str(now): now})
                pipe.zcard(redis_key)
                pipe.expire(redis_key, window_seconds + 5)
                results = pipe.execute()

                current_count = results[2]
                self._consecutive_failures = 0
                return current_count <= limit
            except (RedisError, ConnectionError, TimeoutError, Exception) as e:
                self._record_failure(e)

        # Tier 2: Resilient Local In-Memory Fallback
        return self._check_local_rate_limit(key, limit, window_seconds, now)

    def _check_local_rate_limit(self, key: str, limit: int, window_seconds: int, now: float) -> bool:
        with self._local_lock:
            # Memory leak protection
            if len(self._local_store) > self._max_local_keys:
                # Evict stale entries
                cutoff = now - window_seconds
                keys_to_delete = [
                    k for k, timestamps in self._local_store.items()
                    if not timestamps or timestamps[-1] < cutoff
                ]
                for k in keys_to_delete[:1000]:
                    del self._local_store[k]

            timestamps = self._local_store[key]
            cutoff = now - window_seconds
            # Filter active window
            self._local_store[key] = [t for t in timestamps if t > cutoff]
            self._local_store[key].append(now)

            return len(self._local_store[key]) <= limit

    def probe_health(self) -> Dict[str, Any]:
        """Probes Redis readiness and latency."""
        if not self.redis:
            return {
                "status": "degraded",
                "tier": "local_fallback",
                "circuit_open": self._circuit_open,
                "error": "Redis client uninitialized"
            }

        t0 = time.time()
        try:
            self.redis.ping()
            latency_ms = round((time.time() - t0) * 1000.0, 2)
            return {
                "status": "ok",
                "tier": "redis",
                "latency_ms": latency_ms,
                "circuit_open": self._circuit_open
            }
        except Exception as e:
            return {
                "status": "degraded",
                "tier": "local_fallback",
                "circuit_open": self._circuit_open,
                "error": str(e)
            }

rate_limiter = RateLimiter()
