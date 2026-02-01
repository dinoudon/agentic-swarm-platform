"""Retry decorators and utilities using tenacity."""

from functools import wraps
from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.utils.logger import get_logger
from src.utils.errors import APIError, RateLimitExceededError

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_on_api_error(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable[[F], F]:
    """Decorator to retry function on API errors with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries in seconds
        max_wait: Maximum wait time between retries in seconds

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: F) -> F:
        @retry(
            retry=retry_if_exception_type((APIError, RateLimitExceededError)),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(min=min_wait, max=max_wait),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @retry(
            retry=retry_if_exception_type((APIError, RateLimitExceededError)),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(min=min_wait, max=max_wait),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        import asyncio
        import inspect

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


# Import logging for before_sleep_log
import logging
