"""Task and task dependency graph models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of tasks that can be executed."""

    CODE_GENERATION = "code_generation"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    TESTING = "testing"


class TaskPriority(str, Enum):
    """Task priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def to_numeric(self) -> int:
        """Convert priority to numeric value for sorting."""
        return {"critical": 4, "high": 3, "medium": 2, "low": 1}[self.value]


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskComplexity(str, Enum):
    """Estimated task complexity."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Task(BaseModel):
    """A single executable task."""

    id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    type: TaskType = Field(..., description="Task type")
    title: str = Field(..., description="Brief task description")
    description: str = Field(..., description="Detailed task requirements")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current status")
    complexity: TaskComplexity = Field(
        default=TaskComplexity.MEDIUM, description="Estimated complexity"
    )

    # Dependencies
    depends_on: list[UUID] = Field(
        default_factory=list, description="Task IDs this task depends on"
    )
    blocks: list[UUID] = Field(
        default_factory=list, description="Task IDs that depend on this task"
    )

    # Context and inputs
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context for execution"
    )
    inputs: dict[str, Any] = Field(default_factory=dict, description="Input data for the task")

    # Execution tracking
    assigned_agent_id: UUID | None = Field(default=None, description="Assigned agent ID")
    started_at: datetime | None = Field(default=None, description="Execution start time")
    completed_at: datetime | None = Field(default=None, description="Execution completion time")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    error_message: str | None = Field(default=None, description="Error message if failed")

    # Results
    result: dict[str, Any] | None = Field(default=None, description="Task execution result")

    def is_ready(self, completed_task_ids: set[UUID]) -> bool:
        """Check if task is ready to execute (all dependencies completed).

        Args:
            completed_task_ids: Set of completed task IDs

        Returns:
            True if all dependencies are completed
        """
        if self.status != TaskStatus.PENDING:
            return False
        return all(dep_id in completed_task_ids for dep_id in self.depends_on)

    def mark_in_progress(self, agent_id: UUID) -> None:
        """Mark task as in progress."""
        self.status = TaskStatus.IN_PROGRESS
        self.assigned_agent_id = agent_id
        self.started_at = datetime.now()

    def mark_completed(self, result: dict[str, Any]) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error
        self.retry_count += 1


class TaskDependencyGraph(BaseModel):
    """Graph structure for managing task dependencies."""

    tasks: dict[UUID, Task] = Field(default_factory=dict, description="Tasks indexed by ID")

    def add_task(self, task: Task) -> None:
        """Add a task to the graph.

        Args:
            task: Task to add
        """
        self.tasks[task.id] = task

        # Update reverse dependencies
        for dep_id in task.depends_on:
            if dep_id in self.tasks:
                if task.id not in self.tasks[dep_id].blocks:
                    self.tasks[dep_id].blocks.append(task.id)

    def get_ready_tasks(self) -> list[Task]:
        """Get tasks that are ready to execute (all dependencies completed).

        Returns:
            List of ready tasks, sorted by priority
        """
        completed_ids = {
            task_id for task_id, task in self.tasks.items() if task.status == TaskStatus.COMPLETED
        }

        ready_tasks = [task for task in self.tasks.values() if task.is_ready(completed_ids)]

        # Sort by priority (highest first) and then by complexity (simplest first)
        ready_tasks.sort(
            key=lambda t: (-t.priority.to_numeric(), t.complexity.value), reverse=False
        )

        return ready_tasks

    def mark_task_completed(self, task_id: UUID, result: dict[str, Any]) -> None:
        """Mark a task as completed.

        Args:
            task_id: ID of completed task
            result: Task result
        """
        if task_id in self.tasks:
            self.tasks[task_id].mark_completed(result)

    def mark_task_failed(self, task_id: UUID, error: str) -> None:
        """Mark a task as failed.

        Args:
            task_id: ID of failed task
            error: Error message
        """
        if task_id in self.tasks:
            self.tasks[task_id].mark_failed(error)

    def is_complete(self) -> bool:
        """Check if all tasks are in terminal state (completed or failed).

        Returns:
            True if all tasks are done
        """
        terminal_states = {TaskStatus.COMPLETED, TaskStatus.FAILED}
        return all(task.status in terminal_states for task in self.tasks.values())

    def validate_no_cycles(self) -> bool:
        """Validate that there are no circular dependencies.

        Returns:
            True if no cycles detected

        Raises:
            DependencyCycleError: If a cycle is detected
        """
        from src.utils.errors import DependencyCycleError

        visited = set()
        path = []

        def dfs(task_id: UUID) -> bool:
            if task_id in path:
                # Found a cycle
                cycle_start = path.index(task_id)
                cycle = [str(self.tasks[tid].title) for tid in path[cycle_start:]] + [
                    self.tasks[task_id].title
                ]
                raise DependencyCycleError(cycle)

            if task_id in visited:
                return True

            visited.add(task_id)
            path.append(task_id)

            task = self.tasks[task_id]
            for dep_id in task.depends_on:
                if dep_id in self.tasks:
                    dfs(dep_id)

            path.pop()
            return True

        for task_id in self.tasks:
            if task_id not in visited:
                dfs(task_id)

        return True

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the task graph.

        Returns:
            Dictionary with task statistics
        """
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(
                1 for task in self.tasks.values() if task.status == status
            )

        type_counts = {}
        for task_type in TaskType:
            type_counts[task_type.value] = sum(
                1 for task in self.tasks.values() if task.type == task_type
            )

        return {
            "total": len(self.tasks),
            "by_status": status_counts,
            "by_type": type_counts,
            "ready": len(self.get_ready_tasks()),
        }
