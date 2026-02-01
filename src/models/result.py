"""Result models for task execution and aggregation."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ResultStatus(str, Enum):
    """Result status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ArtifactType(str, Enum):
    """Types of generated artifacts."""

    CODE = "code"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    TEST = "test"
    OTHER = "other"


class Artifact(BaseModel):
    """A generated output artifact."""

    type: ArtifactType = Field(..., description="Type of artifact")
    name: str = Field(..., description="Artifact name or identifier")
    content: str = Field(..., description="Artifact content")
    language: str | None = Field(default=None, description="Programming/markup language")
    file_path: str | None = Field(default=None, description="Suggested file path")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TaskResult(BaseModel):
    """Result from a single task execution."""

    task_id: UUID = Field(..., description="Task ID")
    status: ResultStatus = Field(..., description="Execution status")
    artifacts: list[Artifact] = Field(default_factory=list, description="Generated artifacts")

    # Execution details
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime = Field(..., description="Completion timestamp")
    duration_seconds: float = Field(..., description="Execution duration")

    # Token usage
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    total_tokens: int = Field(default=0, description="Total tokens used")

    # Agent info
    agent_id: UUID = Field(..., description="Agent that executed the task")
    agent_type: str = Field(..., description="Type of agent")

    # Error handling
    error_message: str | None = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries")

    # Additional context
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AggregatedResult(BaseModel):
    """Aggregated results from all tasks."""

    # Overall status
    status: ResultStatus = Field(..., description="Overall execution status")
    total_tasks: int = Field(..., description="Total number of tasks")
    successful_tasks: int = Field(..., description="Number of successful tasks")
    failed_tasks: int = Field(..., description="Number of failed tasks")

    # Results
    task_results: list[TaskResult] = Field(..., description="Individual task results")
    artifacts_by_type: dict[str, list[Artifact]] = Field(
        default_factory=dict, description="Artifacts grouped by type"
    )

    # Execution timeline
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: datetime = Field(..., description="Execution completion time")
    total_duration_seconds: float = Field(..., description="Total duration")

    # Resource usage
    total_input_tokens: int = Field(default=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, description="Total output tokens")
    total_tokens: int = Field(default=0, description="Total tokens")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost in USD")

    # Summary
    executive_summary: str | None = Field(
        default=None, description="High-level summary of results"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Recommendations based on results"
    )

    # Metadata
    prd_title: str | None = Field(default=None, description="Source PRD title")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_success_rate(self) -> float:
        """Calculate task success rate.

        Returns:
            Success rate as percentage (0-100)
        """
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100

    def get_artifacts_of_type(self, artifact_type: ArtifactType) -> list[Artifact]:
        """Get all artifacts of a specific type.

        Args:
            artifact_type: Type of artifacts to retrieve

        Returns:
            List of artifacts of the specified type
        """
        return self.artifacts_by_type.get(artifact_type.value, [])

    def generate_summary_stats(self) -> dict[str, Any]:
        """Generate summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": f"{self.get_success_rate():.1f}%",
            "total_duration": f"{self.total_duration_seconds:.2f}s",
            "total_tokens": self.total_tokens,
            "estimated_cost": f"${self.estimated_cost_usd:.4f}",
            "artifacts_generated": sum(len(arts) for arts in self.artifacts_by_type.values()),
        }
