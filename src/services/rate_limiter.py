"""Rate limiter for API requests using token bucket algorithm."""

import asyncio
import time
from typing import Optional

from src.models.config import RateLimitConfig
from src.utils.errors import RateLimitExceededError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(self, config: RateLimitConfig):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config

        # Request rate limiting
        self.max_requests_per_minute = config.max_requests_per_minute
        self.request_tokens = float(config.max_requests_per_minute)
        self.last_request_refill = time.time()

        # Token rate limiting
        self.max_tokens_per_minute = config.max_tokens_per_minute
        self.token_tokens = float(config.max_tokens_per_minute)
        self.last_token_refill = time.time()

        # Concurrent requests
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)

        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """Acquire permission to make an API request.

        Args:
            estimated_tokens: Estimated tokens for the request

        Raises:
            RateLimitExceededError: If rate limits would be exceeded
        """
        while True:
            async with self.lock:
                # Refill request tokens
                await self._refill_request_tokens()

                # Refill token bucket
                await self._refill_token_tokens()

                # Check if we have enough tokens
                wait_time = 0.0

                if self.request_tokens < 1:
                    wait_time = max(wait_time, 60.0 - (time.time() - self.last_request_refill))
                    logger.warning(
                        "Request rate limit reached, waiting",
                        wait_time=f"{wait_time:.2f}s",
                    )

                if self.token_tokens < estimated_tokens:
                    token_wait = 60.0 - (time.time() - self.last_token_refill)
                    if token_wait > wait_time:
                        wait_time = token_wait
                        logger.warning(
                            "Token rate limit reached, waiting",
                            wait_time=f"{wait_time:.2f}s",
                            estimated_tokens=estimated_tokens,
                        )

                if wait_time <= 0:
                    # Consume tokens
                    self.request_tokens -= 1
                    self.token_tokens -= estimated_tokens

                    logger.debug(
                        "Rate limit tokens acquired",
                        request_tokens_remaining=f"{self.request_tokens:.1f}",
                        token_tokens_remaining=f"{self.token_tokens:.0f}",
                    )
                    break

            # Wait outside the lock
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        # Acquire semaphore for concurrent request limiting
        await self.semaphore.acquire()

    def release(self) -> None:
        """Release a concurrent request slot."""
        self.semaphore.release()

    async def _refill_request_tokens(self) -> None:
        """Refill request tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_request_refill

        if elapsed >= 60.0:
            # Full refill after a minute
            self.request_tokens = float(self.max_requests_per_minute)
            self.last_request_refill = now
        else:
            # Partial refill based on elapsed time
            refill_amount = (elapsed / 60.0) * self.max_requests_per_minute
            self.request_tokens = min(
                self.request_tokens + refill_amount, float(self.max_requests_per_minute)
            )
            if refill_amount > 0:
                self.last_request_refill = now

    async def _refill_token_tokens(self) -> None:
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_token_refill

        if elapsed >= 60.0:
            # Full refill after a minute
            self.token_tokens = float(self.max_tokens_per_minute)
            self.last_token_refill = now
        else:
            # Partial refill based on elapsed time
            refill_amount = (elapsed / 60.0) * self.max_tokens_per_minute
            self.token_tokens = min(
                self.token_tokens + refill_amount, float(self.max_tokens_per_minute)
            )
            if refill_amount > 0:
                self.last_token_refill = now

    async def __aenter__(self) -> "RateLimiter":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: object) -> None:
        """Context manager exit."""
        self.release()
