"""Base agent class for all specialized agents."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from anthropic.types import Usage

from src.models.agent import Agent, AgentStatus
from src.models.result import Artifact, ResultStatus, TaskResult
from src.models.task import Task
from src.services.claude_client import ClaudeClient
from src.services.rate_limiter import RateLimiter
from src.utils.errors import AgentError, TaskExecutionError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        agent: Agent,
        claude_client: ClaudeClient,
        rate_limiter: RateLimiter,
    ):
        """Initialize base agent.

        Args:
            agent: Agent model instance
            claude_client: Claude API client
            rate_limiter: Rate limiter for API calls
        """
        self.agent = agent
        self.claude_client = claude_client
        self.rate_limiter = rate_limiter

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent type.

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    async def process_task(self, task: Task, response: str) -> list[Artifact]:
        """Process Claude's response and extract artifacts.

        Args:
            task: The task being executed
            response: Claude's response text

        Returns:
            List of generated artifacts
        """
        pass

    async def execute_task(self, task: Task) -> TaskResult:
        """Execute a task.

        Args:
            task: Task to execute

        Returns:
            Task result

        Raises:
            TaskExecutionError: If task execution fails
        """
        task_start = datetime.now()
        logger.info(
            "Agent executing task",
            agent_id=str(self.agent.id),
            agent_type=self.agent.type.value,
            task_id=str(task.id),
            task_title=task.title,
        )

        # Update agent status
        self.agent.status = AgentStatus.BUSY
        self.agent.current_task_id = task.id

        try:
            # Build messages with task context
            messages = self._build_messages(task)

            # Acquire rate limit
            estimated_tokens = len(str(messages)) // 4  # Rough estimate
            await self.rate_limiter.acquire(estimated_tokens)

            try:
                # Call Claude API
                response, usage = await self.claude_client.create_message(
                    system=self.get_system_prompt(),
                    messages=messages,
                )

                # Process response to extract artifacts
                artifacts = await self.process_task(task, response)

                # Update metrics
                duration = (datetime.now() - task_start).total_seconds()
                self.agent.metrics.update_on_success(
                    duration=duration, tokens=usage.input_tokens + usage.output_tokens
                )

                # Mark agent as idle
                self.agent.status = AgentStatus.IDLE
                self.agent.complete_current_task()

                # Build result
                result = TaskResult(
                    task_id=task.id,
                    status=ResultStatus.SUCCESS,
                    artifacts=artifacts,
                    started_at=task_start,
                    completed_at=datetime.now(),
                    duration_seconds=duration,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    total_tokens=usage.input_tokens + usage.output_tokens,
                    agent_id=self.agent.id,
                    agent_type=self.agent.type.value,
                )

                logger.info(
                    "Task completed successfully",
                    task_id=str(task.id),
                    artifacts=len(artifacts),
                    tokens=result.total_tokens,
                )

                return result

            finally:
                self.rate_limiter.release()

        except Exception as e:
            # Update metrics
            self.agent.metrics.update_on_failure()
            self.agent.status = AgentStatus.ERROR

            duration = (datetime.now() - task_start).total_seconds()
            error_msg = str(e)

            logger.error(
                "Task execution failed",
                task_id=str(task.id),
                agent_id=str(self.agent.id),
                error=error_msg,
            )

            # Build error result
            result = TaskResult(
                task_id=task.id,
                status=ResultStatus.FAILED,
                artifacts=[],
                started_at=task_start,
                completed_at=datetime.now(),
                duration_seconds=duration,
                agent_id=self.agent.id,
                agent_type=self.agent.type.value,
                error_message=error_msg,
                retry_count=task.retry_count,
            )

            # Reset agent to idle for next task
            self.agent.status = AgentStatus.IDLE
            self.agent.complete_current_task()

            return result

    def _build_messages(self, task: Task) -> list[dict[str, str]]:
        """Build message list for Claude API.

        Args:
            task: Task to execute

        Returns:
            List of messages
        """
        # Build user message with task details
        user_message = f"""# Task: {task.title}

## Description
{task.description}

## Priority
{task.priority.value}

## Complexity
{task.complexity.value}

## Additional Context
{self._format_context(task.context)}

## Inputs
{self._format_inputs(task.inputs)}

Please complete this task according to your specialization."""

        return [{"role": "user", "content": user_message}]

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context dictionary for display.

        Args:
            context: Context dictionary

        Returns:
            Formatted string
        """
        if not context:
            return "None"
        lines = []
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _format_inputs(self, inputs: dict[str, Any]) -> str:
        """Format inputs dictionary for display.

        Args:
            inputs: Inputs dictionary

        Returns:
            Formatted string
        """
        if not inputs:
            return "None"
        lines = []
        for key, value in inputs.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
