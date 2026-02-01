"""Agent models and configuration."""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.models.task import TaskType


class AgentType(str, Enum):
    """Types of specialized agents."""

    CODE_GENERATOR = "code_generator"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    TESTING = "testing"


class AgentStatus(str, Enum):
    """Agent status."""

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class AgentCapability(BaseModel):
    """Capabilities of an agent."""

    task_types: list[TaskType] = Field(..., description="Task types this agent can handle")
    max_concurrent_tasks: int = Field(default=1, description="Max concurrent tasks")
    specializations: list[str] = Field(
        default_factory=list, description="Specific specializations"
    )


class AgentMetrics(BaseModel):
    """Metrics for agent performance tracking."""

    tasks_completed: int = Field(default=0, description="Total tasks completed")
    tasks_failed: int = Field(default=0, description="Total tasks failed")
    total_tokens_used: int = Field(default=0, description="Total tokens consumed")
    total_execution_time: float = Field(default=0.0, description="Total execution time in seconds")
    average_task_duration: float = Field(
        default=0.0, description="Average task duration in seconds"
    )

    def update_on_success(self, duration: float, tokens: int) -> None:
        """Update metrics after successful task completion."""
        self.tasks_completed += 1
        self.total_tokens_used += tokens
        self.total_execution_time += duration
        if self.tasks_completed > 0:
            self.average_task_duration = self.total_execution_time / self.tasks_completed

    def update_on_failure(self) -> None:
        """Update metrics after task failure."""
        self.tasks_failed += 1


class Agent(BaseModel):
    """An agent instance that can execute tasks."""

    id: UUID = Field(default_factory=uuid4, description="Unique agent identifier")
    type: AgentType = Field(..., description="Agent type")
    status: AgentStatus = Field(default=AgentStatus.IDLE, description="Current status")
    capabilities: AgentCapability = Field(..., description="Agent capabilities")

    # Current state
    current_task_id: UUID | None = Field(default=None, description="Currently executing task ID")
    task_queue: list[UUID] = Field(default_factory=list, description="Queued task IDs")

    # Tracking
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    last_activity: datetime = Field(
        default_factory=datetime.now, description="Last activity timestamp"
    )
    metrics: AgentMetrics = Field(
        default_factory=AgentMetrics, description="Performance metrics"
    )

    def can_handle_task(self, task_type: TaskType) -> bool:
        """Check if agent can handle a specific task type.

        Args:
            task_type: Type of task

        Returns:
            True if agent can handle this task type
        """
        return task_type in self.capabilities.task_types

    def is_available(self) -> bool:
        """Check if agent is available to take new tasks.

        Returns:
            True if agent is idle and can accept tasks
        """
        return (
            self.status == AgentStatus.IDLE
            and len(self.task_queue) < self.capabilities.max_concurrent_tasks
        )

    def assign_task(self, task_id: UUID) -> None:
        """Assign a task to this agent.

        Args:
            task_id: ID of task to assign
        """
        self.task_queue.append(task_id)
        if not self.current_task_id:
            self.current_task_id = task_id
            self.status = AgentStatus.BUSY
        self.last_activity = datetime.now()

    def complete_current_task(self) -> None:
        """Mark current task as complete and move to next."""
        if self.current_task_id and self.current_task_id in self.task_queue:
            self.task_queue.remove(self.current_task_id)

        if self.task_queue:
            self.current_task_id = self.task_queue[0]
            self.status = AgentStatus.BUSY
        else:
            self.current_task_id = None
            self.status = AgentStatus.IDLE

        self.last_activity = datetime.now()
