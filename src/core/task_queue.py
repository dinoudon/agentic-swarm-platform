"""Task queue with dependency management."""

import asyncio
from typing import Any
from uuid import UUID

from src.models.task import Task, TaskDependencyGraph, TaskStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TaskQueue:
    """Task queue that manages task execution based on dependencies."""

    def __init__(self, task_graph: TaskDependencyGraph):
        """Initialize task queue.

        Args:
            task_graph: Task dependency graph
        """
        self.task_graph = task_graph
        self._lock = asyncio.Lock()

    async def get_ready_tasks(self, limit: int | None = None) -> list[Task]:
        """Get tasks that are ready to execute.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of ready tasks
        """
        async with self._lock:
            ready_tasks = self.task_graph.get_ready_tasks()
            if limit:
                return ready_tasks[:limit]
            return ready_tasks

    async def mark_task_started(self, task_id: UUID, agent_id: UUID) -> None:
        """Mark a task as started.

        Args:
            task_id: Task ID
            agent_id: Agent ID executing the task
        """
        async with self._lock:
            if task_id in self.task_graph.tasks:
                task = self.task_graph.tasks[task_id]
                task.mark_in_progress(agent_id)
                logger.info("Task started", task_id=str(task_id), title=task.title)

    async def mark_task_completed(self, task_id: UUID, result: dict[str, Any]) -> None:
        """Mark a task as completed.

        Args:
            task_id: Task ID
            result: Task result data
        """
        async with self._lock:
            self.task_graph.mark_task_completed(task_id, result)
            if task_id in self.task_graph.tasks:
                task = self.task_graph.tasks[task_id]
                logger.info(
                    "Task completed",
                    task_id=str(task_id),
                    title=task.title,
                    unblocks=len(task.blocks),
                )

    async def mark_task_failed(
        self, task_id: UUID, error: str, should_retry: bool = True
    ) -> bool:
        """Mark a task as failed.

        Args:
            task_id: Task ID
            error: Error message
            should_retry: Whether this task should be retried

        Returns:
            True if task was marked for retry, False if permanently failed
        """
        async with self._lock:
            if task_id in self.task_graph.tasks:
                task = self.task_graph.tasks[task_id]

                if should_retry and task.retry_count < 3:  # Max retries
                    # Reset to pending for retry
                    task.status = TaskStatus.PENDING
                    task.assigned_agent_id = None
                    task.error_message = error
                    logger.warning(
                        "Task failed, will retry",
                        task_id=str(task_id),
                        title=task.title,
                        retry_count=task.retry_count + 1,
                        error=error,
                    )
                    return True
                else:
                    # Mark as permanently failed
                    self.task_graph.mark_task_failed(task_id, error)
                    logger.error(
                        "Task permanently failed",
                        task_id=str(task_id),
                        title=task.title,
                        error=error,
                    )
                    return False
            return False

    async def is_complete(self) -> bool:
        """Check if all tasks are complete.

        Returns:
            True if all tasks are in terminal state
        """
        async with self._lock:
            return self.task_graph.is_complete()

    async def get_stats(self) -> dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary with queue stats
        """
        async with self._lock:
            return self.task_graph.get_stats()

    async def get_task(self, task_id: UUID) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        async with self._lock:
            return self.task_graph.tasks.get(task_id)

    async def get_all_tasks(self) -> list[Task]:
        """Get all tasks.

        Returns:
            List of all tasks
        """
        async with self._lock:
            return list(self.task_graph.tasks.values())
