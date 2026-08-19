import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


logger = logging.getLogger(
    "telegram-test-series-bot.rate-limiter"
)


# ============================================================
# RATE LIMIT RESULT
# ============================================================

@dataclass
class RateLimitResult:

    allowed: bool

    remaining: int

    retry_after: int = 0

    reason: str = ""


# ============================================================
# USER RATE LIMITER
# ============================================================

class UserRateLimiter:
    """
    Per-user rate limiter.

    Example:

        10 requests / 60 seconds

    इससे कोई एक user लगातार बहुत ज्यादा requests भेजकर
    पूरे bot को overload नहीं कर पाएगा।
    """

    def __init__(
        self,
        max_requests: int = 10,
        window_seconds: int = 60,
    ):

        self.max_requests = max(
            1,
            int(max_requests),
        )

        self.window_seconds = max(
            1,
            int(window_seconds),
        )

        self._requests: Dict[
            int,
            Deque[float]
        ] = defaultdict(
            deque
        )

        self._locks: Dict[
            int,
            asyncio.Lock
        ] = {}

        self._global_lock = asyncio.Lock()

    # ========================================================
    # LOCK
    # ========================================================

    async def _get_lock(
        self,
        user_id: int,
    ) -> asyncio.Lock:

        async with self._global_lock:

            if user_id not in self._locks:

                self._locks[
                    user_id
                ] = asyncio.Lock()

            return self._locks[
                user_id
            ]

    # ========================================================
    # CLEAN OLD REQUESTS
    # ========================================================

    def _cleanup(
        self,
        user_id: int,
        now: Optional[float] = None,
    ):

        if now is None:

            now = time.monotonic()

        requests = self._requests[
            user_id
        ]

        cutoff = (
            now
            - self.window_seconds
        )

        while requests:

            if requests[0] > cutoff:
                break

            requests.popleft()

    # ========================================================
    # CHECK
    # ========================================================

    async def check(
        self,
        user_id: int,
        consume: bool = True,
    ) -> RateLimitResult:

        user_id = int(
            user_id
        )

        lock = await self._get_lock(
            user_id
        )

        async with lock:

            now = time.monotonic()

            self._cleanup(
                user_id,
                now,
            )

            requests = self._requests[
                user_id
            ]

            current = len(
                requests
            )

            if current >= self.max_requests:

                if requests:

                    retry_after = max(
                        1,
                        int(
                            requests[0]
                            + self.window_seconds
                            - now
                        ),
                    )

                else:

                    retry_after = (
                        self.window_seconds
                    )

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    reason="rate_limit",
                )

            if consume:

                requests.append(
                    now
                )

            remaining = max(
                0,
                self.max_requests
                - len(requests),
            )

            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after=0,
            )

    # ========================================================
    # ALLOW
    # ========================================================

    async def allow(
        self,
        user_id: int,
    ) -> bool:

        result = await self.check(
            user_id
        )

        return result.allowed

    # ========================================================
    # RESET USER
    # ========================================================

    async def reset(
        self,
        user_id: int,
    ):

        user_id = int(
            user_id
        )

        lock = await self._get_lock(
            user_id
        )

        async with lock:

            self._requests.pop(
                user_id,
                None,
            )

    # ========================================================
    # REMOVE INACTIVE USERS
    # ========================================================

    async def cleanup_all(self):

        now = time.monotonic()

        async with self._global_lock:

            user_ids = list(
                self._requests.keys()
            )

        for user_id in user_ids:

            lock = await self._get_lock(
                user_id
            )

            async with lock:

                self._cleanup(
                    user_id,
                    now,
                )

                if not self._requests[
                    user_id
                ]:

                    self._requests.pop(
                        user_id,
                        None,
                    )


# ============================================================
# GLOBAL USER LIMITER
# ============================================================

try:

    from app.config import CONFIG

    USER_RATE_LIMIT = (
        CONFIG.USER_RATE_LIMIT
    )

    USER_RATE_WINDOW = (
        CONFIG.USER_RATE_WINDOW
    )

except Exception:

    USER_RATE_LIMIT = 10
    USER_RATE_WINDOW = 60


user_rate_limiter = UserRateLimiter(
    max_requests=USER_RATE_LIMIT,
    window_seconds=USER_RATE_WINDOW,
)


# ============================================================
# EXTRACTION RATE LIMITER
# ============================================================

class ExtractionRateLimiter:
    """
    Test extraction के लिए अलग limiter.

    Normal messages और Test extraction को अलग रखा गया है
    ताकि user सामान्य bot features इस्तेमाल कर सके लेकिन
    extraction requests की flooding न कर सके।
    """

    def __init__(
        self,
        max_requests: int = 3,
        window_seconds: int = 60,
    ):

        self.max_requests = max(
            1,
            int(max_requests),
        )

        self.window_seconds = max(
            1,
            int(window_seconds),
        )

        self._requests: Dict[
            int,
            Deque[float]
        ] = defaultdict(
            deque
        )

        self._locks: Dict[
            int,
            asyncio.Lock
        ] = {}

        self._global_lock = asyncio.Lock()

    async def _get_lock(
        self,
        user_id: int,
    ) -> asyncio.Lock:

        async with self._global_lock:

            if user_id not in self._locks:

                self._locks[
                    user_id
                ] = asyncio.Lock()

            return self._locks[
                user_id
            ]

    def _cleanup(
        self,
        user_id: int,
        now: float,
    ):

        requests = self._requests[
            user_id
        ]

        cutoff = (
            now
            - self.window_seconds
        )

        while requests:

            if requests[0] > cutoff:
                break

            requests.popleft()

    async def check(
        self,
        user_id: int,
    ) -> RateLimitResult:

        user_id = int(
            user_id
        )

        lock = await self._get_lock(
            user_id
        )

        async with lock:

            now = time.monotonic()

            self._cleanup(
                user_id,
                now,
            )

            requests = self._requests[
                user_id
            ]

            if len(requests) >= (
                self.max_requests
            ):

                retry_after = max(
                    1,
                    int(
                        requests[0]
                        + self.window_seconds
                        - now
                    ),
                )

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after,
                    reason="extraction_rate_limit",
                )

            requests.append(
                now
            )

            return RateLimitResult(
                allowed=True,
                remaining=(
                    self.max_requests
                    - len(requests)
                ),
            )


try:

    from app.config import CONFIG

    MAX_USER_QUEUE = (
        CONFIG.MAX_USER_QUEUE
    )

except Exception:

    MAX_USER_QUEUE = 3


extraction_rate_limiter = (
    ExtractionRateLimiter(
        max_requests=MAX_USER_QUEUE,
        window_seconds=60,
    )
)


# ============================================================
# ADMIN BYPASS
# ============================================================

def is_admin(
    user_id: int,
) -> bool:

    try:

        from app.config import CONFIG

        return int(user_id) in (
            CONFIG.ADMIN_IDS
        )

    except Exception:

        return False


async def check_user_rate_limit(
    user_id: int,
) -> RateLimitResult:

    # Admin पर सामान्य rate limit लागू नहीं होगी।

    if is_admin(
        user_id
    ):

        return RateLimitResult(
            allowed=True,
            remaining=999999,
        )

    return await user_rate_limiter.check(
        user_id
    )


async def check_extraction_limit(
    user_id: int,
) -> RateLimitResult:

    # Admin extraction limit से bypass कर सकता है।

    if is_admin(
        user_id
    ):

        return RateLimitResult(
            allowed=True,
            remaining=999999,
        )

    return await extraction_rate_limiter.check(
        user_id
    )


# ============================================================
# RATE LIMIT MESSAGE
# ============================================================

def rate_limit_message(
    result: RateLimitResult,
) -> str:

    if result.allowed:

        return (
            "✅ Request accepted."
        )

    retry = max(
        1,
        result.retry_after,
    )

    return (
        "⏳ अभी requests बहुत ज्यादा हैं।\n\n"
        f"कृपया {retry} सेकंड बाद दोबारा try करें।"
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "RateLimitResult",
    "UserRateLimiter",
    "ExtractionRateLimiter",
    "user_rate_limiter",
    "extraction_rate_limiter",
    "check_user_rate_limit",
    "check_extraction_limit",
    "rate_limit_message",
]
