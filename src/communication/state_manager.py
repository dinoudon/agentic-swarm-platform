"""Centralized state management for the swarm."""

import asyncio
from typing import Any
from uuid import UUID

from src.models.agent import Agent, AgentStatus
from src.models.task import Task, TaskStatus
from src.models.result import TaskResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StateManager:
    """Manages centralized state for tasks, agents, and results."""

    def __init__(self) -> None:
        """Initialize state manager."""
        self._lock = asyncio.Lock()
        self._tasks: dict[UUID, Task] = {}
        self._agents: dict[UUID, Agent] = {}
        self._results: dict[UUID, TaskResult] = {}
        self._global_context: dict[str, Any] = {}

    # Task management
    async def add_task(self, task: Task) -> None:
        """Add a task to state.

        Args:
            task: Task to add
        """
        async with self._lock:
            self._tasks[task.id] = task
            logger.debug("Task added to state", task_id=str(task.id), title=task.title)

    async def get_task(self, task_id: UUID) -> Task | None:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(self, task: Task) -> None:
        """Update a task in state.

        Args:
            task: Updated task
        """
        async with self._lock:
            self._tasks[task.id] = task
            logger.debug("Task updated in state", task_id=str(task.id), status=task.status.value)

    async def get_all_tasks(self) -> list[Task]:
        """Get all tasks.

        Returns:
            List of all tasks
        """
        async with self._lock:
            return list(self._tasks.values())

    async def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """Get tasks by status.

        Args:
            status: Task status to filter by

        Returns:
            List of tasks with the given status
        """
        async with self._lock:
            return [task for task in self._tasks.values() if task.status == status]

    # Agent management
    async def add_agent(self, agent: Agent) -> None:
        """Add an agent to state.

        Args:
            agent: Agent to add
        """
        async with self._lock:
            self._agents[agent.id] = agent
            logger.debug("Agent added to state", agent_id=str(agent.id), type=agent.type.value)

    async def get_agent(self, agent_id: UUID) -> Agent | None:
        """Get an agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent if found, None otherwise
        """
        async with self._lock:
            return self._agents.get(agent_id)

    async def update_agent(self, agent: Agent) -> None:
        """Update an agent in state.

        Args:
            agent: Updated agent
        """
        async with self._lock:
            self._agents[agent.id] = agent
            logger.debug("Agent updated in state", agent_id=str(agent.id), status=agent.status.value)

    async def get_all_agents(self) -> list[Agent]:
        """Get all agents.

        Returns:
            List of all agents
        """
        async with self._lock:
            return list(self._agents.values())

    async def get_available_agents(self) -> list[Agent]:
        """Get agents that are available to take tasks.

        Returns:
            List of available agents
        """
        async with self._lock:
            return [agent for agent in self._agents.values() if agent.is_available()]

    # Result management
    async def add_result(self, result: TaskResult) -> None:
        """Add a task result to state.

        Args:
            result: Task result to add
        """
        async with self._lock:
            self._results[result.task_id] = result
            logger.debug("Result added to state", task_id=str(result.task_id))

    async def get_result(self, task_id: UUID) -> TaskResult | None:
        """Get a result by task ID.

        Args:
            task_id: Task ID

        Returns:
            TaskResult if found, None otherwise
        """
        async with self._lock:
            return self._results.get(task_id)

    async def get_all_results(self) -> list[TaskResult]:
        """Get all results.

        Returns:
            List of all task results
        """
        async with self._lock:
            return list(self._results.values())

    # Global context management
    async def set_context(self, key: str, value: Any) -> None:
        """Set a global context value.

        Args:
            key: Context key
            value: Context value
        """
        async with self._lock:
            self._global_context[key] = value
            logger.debug("Context updated", key=key)

    async def get_context(self, key: str, default: Any = None) -> Any:
        """Get a global context value.

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        async with self._lock:
            return self._global_context.get(key, default)

    async def get_all_context(self) -> dict[str, Any]:
        """Get all global context.

        Returns:
            Dictionary of all context values
        """
        async with self._lock:
            return self._global_context.copy()

    # State queries
    async def get_stats(self) -> dict[str, Any]:
        """Get state statistics.

        Returns:
            Dictionary with state statistics
        """
        async with self._lock:
            task_status_counts = {}
            for status in TaskStatus:
                task_status_counts[status.value] = sum(
                    1 for task in self._tasks.values() if task.status == status
                )

            agent_status_counts = {}
            for status in AgentStatus:
                agent_status_counts[status.value] = sum(
                    1 for agent in self._agents.values() if agent.status == status
                )

            return {
                "total_tasks": len(self._tasks),
                "total_agents": len(self._agents),
                "total_results": len(self._results),
                "task_status": task_status_counts,
                "agent_status": agent_status_counts,
            }

    async def reset(self) -> None:
        """Reset all state (for testing or cleanup)."""
        async with self._lock:
            self._tasks.clear()
            self._agents.clear()
            self._results.clear()
            self._global_context.clear()
            logger.info("State manager reset")
