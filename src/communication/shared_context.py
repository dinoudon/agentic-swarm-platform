"""Shared context store for cross-agent communication."""

import asyncio
from typing import Any
from uuid import UUID

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SharedContext:
    """Shared context store that allows agents to share information."""

    def __init__(self) -> None:
        """Initialize shared context."""
        self._lock = asyncio.Lock()
        self._context: dict[str, Any] = {}
        self._scopes: dict[str, dict[str, Any]] = {}  # Scoped contexts

    async def set(self, key: str, value: Any, scope: str | None = None) -> None:
        """Set a value in the shared context.

        Args:
            key: Context key
            value: Value to store
            scope: Optional scope (e.g., PRD ID, execution ID)
        """
        async with self._lock:
            if scope:
                if scope not in self._scopes:
                    self._scopes[scope] = {}
                self._scopes[scope][key] = value
                logger.debug("Scoped context set", key=key, scope=scope)
            else:
                self._context[key] = value
                logger.debug("Global context set", key=key)

    async def get(self, key: str, scope: str | None = None, default: Any = None) -> Any:
        """Get a value from the shared context.

        Args:
            key: Context key
            scope: Optional scope to look in
            default: Default value if not found

        Returns:
            Stored value or default
        """
        async with self._lock:
            if scope and scope in self._scopes:
                return self._scopes[scope].get(key, default)
            return self._context.get(key, default)

    async def get_all(self, scope: str | None = None) -> dict[str, Any]:
        """Get all context values.

        Args:
            scope: Optional scope to get values from

        Returns:
            Dictionary of all values in the scope
        """
        async with self._lock:
            if scope and scope in self._scopes:
                return self._scopes[scope].copy()
            return self._context.copy()

    async def delete(self, key: str, scope: str | None = None) -> bool:
        """Delete a value from the shared context.

        Args:
            key: Context key to delete
            scope: Optional scope

        Returns:
            True if key was deleted, False if not found
        """
        async with self._lock:
            if scope and scope in self._scopes:
                if key in self._scopes[scope]:
                    del self._scopes[scope][key]
                    logger.debug("Scoped context deleted", key=key, scope=scope)
                    return True
            elif key in self._context:
                del self._context[key]
                logger.debug("Global context deleted", key=key)
                return True
            return False

    async def clear_scope(self, scope: str) -> None:
        """Clear all values in a scope.

        Args:
            scope: Scope to clear
        """
        async with self._lock:
            if scope in self._scopes:
                self._scopes[scope].clear()
                logger.debug("Scope cleared", scope=scope)

    async def delete_scope(self, scope: str) -> None:
        """Delete an entire scope.

        Args:
            scope: Scope to delete
        """
        async with self._lock:
            if scope in self._scopes:
                del self._scopes[scope]
                logger.debug("Scope deleted", scope=scope)

    async def clear(self) -> None:
        """Clear all context (global and scoped)."""
        async with self._lock:
            self._context.clear()
            self._scopes.clear()
            logger.debug("All context cleared")

    async def has(self, key: str, scope: str | None = None) -> bool:
        """Check if a key exists in context.

        Args:
            key: Context key
            scope: Optional scope

        Returns:
            True if key exists
        """
        async with self._lock:
            if scope and scope in self._scopes:
                return key in self._scopes[scope]
            return key in self._context

    async def get_scope_keys(self, scope: str) -> list[str]:
        """Get all keys in a scope.

        Args:
            scope: Scope to query

        Returns:
            List of keys in the scope
        """
        async with self._lock:
            if scope in self._scopes:
                return list(self._scopes[scope].keys())
            return []
