"""Event bus for pub/sub communication between components."""

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

from src.utils.logger import get_logger

logger = get_logger(__name__)


EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """Simple event bus for asynchronous pub/sub messaging."""

    def __init__(self) -> None:
        """Initialize event bus."""
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._event_history: list[dict[str, Any]] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to handle the event
        """
        self._subscribers[event_type].append(handler)
        logger.debug("Event subscription added", event_type=event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler to remove
        """
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug("Event subscription removed", event_type=event_type)

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event data
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Store in history
        self._event_history.append(event)

        # Trim history if too long
        if len(self._event_history) > 1000:
            self._event_history = self._event_history[-500:]

        logger.debug("Event published", event_type=event_type)

        # Notify all subscribers
        handlers = self._subscribers.get(event_type, [])
        if handlers:
            await asyncio.gather(
                *[handler(event["data"]) for handler in handlers],
                return_exceptions=True,
            )

    def get_event_history(self, event_type: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get event history.

        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        events = self._event_history
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return events[-limit:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()


# Event type constants
class EventTypes:
    """Standard event types used in the system."""

    # Task events
    TASK_QUEUED = "task.queued"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_RETRYING = "task.retrying"

    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_IDLE = "agent.idle"
    AGENT_BUSY = "agent.busy"
    AGENT_ERROR = "agent.error"
    AGENT_SHUTDOWN = "agent.shutdown"

    # Orchestration events
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"

    # Progress events
    PROGRESS_UPDATE = "progress.update"
