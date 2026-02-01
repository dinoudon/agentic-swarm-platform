"""Custom exceptions for the agentic swarm platform."""


class SwarmError(Exception):
    """Base exception for all swarm-related errors."""

    pass


class PRDParseError(SwarmError):
    """Raised when PRD parsing or validation fails."""

    pass


class TaskExecutionError(SwarmError):
    """Raised when a task execution fails."""

    def __init__(self, task_id: str, message: str, original_error: Exception | None = None):
        self.task_id = task_id
        self.original_error = original_error
        super().__init__(f"Task {task_id} failed: {message}")


class AgentError(SwarmError):
    """Raised when an agent encounters an error."""

    def __init__(self, agent_id: str, message: str, original_error: Exception | None = None):
        self.agent_id = agent_id
        self.original_error = original_error
        super().__init__(f"Agent {agent_id} error: {message}")


class DependencyCycleError(SwarmError):
    """Raised when a circular dependency is detected in the task graph."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class RateLimitExceededError(SwarmError):
    """Raised when API rate limits are exceeded."""

    pass


class ConfigurationError(SwarmError):
    """Raised when configuration is invalid or missing."""

    pass


class APIError(SwarmError):
    """Raised when Claude API calls fail."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)
