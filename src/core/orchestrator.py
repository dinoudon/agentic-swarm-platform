"""Main orchestrator for coordinating PRD execution."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agents.agent_pool import AgentPool
from src.communication.event_bus import EventBus, EventTypes
from src.communication.shared_context import SharedContext
from src.communication.state_manager import StateManager
from src.core.prd_parser import PRDParser
from src.core.result_aggregator import ResultAggregator
from src.core.task_queue import TaskQueue
from src.models.config import SwarmConfig
from src.models.result import AggregatedResult, TaskResult
from src.models.task import TaskStatus
from src.services.claude_client import ClaudeClient
from src.services.claude_code_backend import ClaudeCodeBackend
from src.services.interactive_backend import InteractiveBackend
from src.services.cost_tracker import CostTracker
from src.services.rate_limiter import RateLimiter
from src.utils.logger import get_logger
from src.utils.errors import ConfigurationError

logger = get_logger(__name__)


class Orchestrator:
    """Main orchestrator for PRD execution."""

    def __init__(self, config: SwarmConfig):
        """Initialize orchestrator.

        Args:
            config: Swarm configuration
        """
        self.config = config

        # Initialize services based on backend type
        backend_type = config.backend.type

        if backend_type == "anthropic":
            if not config.anthropic.api_key:
                raise ConfigurationError("API key required for Anthropic backend")
            self.claude_client = ClaudeClient(config.anthropic)
            logger.info("Using Anthropic API backend (official API)")

        elif backend_type == "interactive":
            self.claude_client = InteractiveBackend()  # type: ignore
            logger.info("Using Interactive backend (manual, ToS-compliant)")

        else:
            raise ConfigurationError(f"Unknown backend type: {backend_type}")

        self.rate_limiter = RateLimiter(config.rate_limit)
        self.cost_tracker = CostTracker()

        # Initialize communication layer
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.shared_context = SharedContext()

        # Initialize core components
        self.prd_parser = PRDParser(self.claude_client)
        self.result_aggregator = ResultAggregator(self.claude_client, self.cost_tracker)
        self.agent_pool = AgentPool(config.agent_pool, self.claude_client, self.rate_limiter)

        # Task queue (initialized per execution)
        self.task_queue: TaskQueue | None = None

        # Results storage
        self.task_results: list[TaskResult] = []

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for orchestration events."""

        async def on_task_completed(data: dict[str, Any]) -> None:
            logger.info("Task completed event", task_id=data.get("task_id"))

        async def on_task_failed(data: dict[str, Any]) -> None:
            logger.error("Task failed event", task_id=data.get("task_id"), error=data.get("error"))

        async def on_agent_idle(data: dict[str, Any]) -> None:
            logger.debug("Agent idle event", agent_id=data.get("agent_id"))

        self.event_bus.subscribe(EventTypes.TASK_COMPLETED, on_task_completed)
        self.event_bus.subscribe(EventTypes.TASK_FAILED, on_task_failed)
        self.event_bus.subscribe(EventTypes.AGENT_IDLE, on_agent_idle)

    async def execute_prd_file(self, prd_path: Path) -> AggregatedResult:
        """Execute a PRD from file.

        Args:
            prd_path: Path to PRD file

        Returns:
            Aggregated execution result
        """
        execution_start = datetime.now()
        logger.info("Starting PRD execution", prd_path=str(prd_path))

        # Publish execution started event
        await self.event_bus.publish(
            EventTypes.EXECUTION_STARTED, {"prd_path": str(prd_path), "start_time": execution_start}
        )

        try:
            # Step 1: Parse PRD
            logger.info("Parsing PRD")
            prd = await self.prd_parser.parse_file(prd_path)
            logger.info("PRD parsed", title=prd.metadata.title)

            # Step 2: Slice into tasks
            logger.info("Slicing PRD into tasks")
            task_graph = await self.prd_parser.slice_into_tasks(prd)
            stats = task_graph.get_stats()
            logger.info("Tasks created", **stats)

            # Step 3: Initialize task queue
            self.task_queue = TaskQueue(task_graph)

            # Step 4: Initialize agent pool
            logger.info("Initializing agent pool")
            await self.agent_pool.initialize()
            pool_stats = await self.agent_pool.get_stats()
            logger.info("Agent pool ready", **pool_stats)

            # Step 5: Execute tasks
            logger.info("Starting execution loop")
            await self._execution_loop()

            # Step 6: Aggregate results
            execution_end = datetime.now()
            logger.info("Aggregating results")
            aggregated_result = await self.result_aggregator.aggregate(
                self.task_results, prd, execution_start, execution_end
            )

            # Publish execution completed event
            await self.event_bus.publish(
                EventTypes.EXECUTION_COMPLETED,
                {
                    "status": aggregated_result.status.value,
                    "duration": aggregated_result.total_duration_seconds,
                    "total_tasks": aggregated_result.total_tasks,
                },
            )

            logger.info(
                "PRD execution completed",
                status=aggregated_result.status.value,
                duration=f"{aggregated_result.total_duration_seconds:.2f}s",
                success_rate=f"{aggregated_result.get_success_rate():.1f}%",
            )

            return aggregated_result

        except Exception as e:
            logger.error("PRD execution failed", error=str(e))
            await self.event_bus.publish(EventTypes.EXECUTION_FAILED, {"error": str(e)})
            raise

        finally:
            # Cleanup
            await self.agent_pool.shutdown()

    async def _execution_loop(self) -> None:
        """Main execution loop for processing tasks.

        This is the CORE LOGIC that coordinates parallel task execution.
        """
        if not self.task_queue:
            raise RuntimeError("Task queue not initialized")

        iteration = 0
        max_iterations = 100000  # Safety limit (increased for continuous scheduling)

        # Track running tasks
        pending_futures = set()

        while not await self.task_queue.is_complete() and iteration < max_iterations:
            iteration += 1

            # Get ready tasks and available agents
            ready_tasks = await self.task_queue.get_ready_tasks()
            available_agents = await self.agent_pool.get_available_agents()

            if not ready_tasks and not pending_futures:
                # No ready tasks and nothing running - check if we're done or stuck
                stats = await self.task_queue.get_stats()
                in_progress = stats["by_status"].get(TaskStatus.IN_PROGRESS.value, 0)

                if in_progress == 0:
                    # No tasks ready and none in progress - we're stuck or done
                    break

                # Should not happen if logic is correct, but safe fallback
                await asyncio.sleep(self.config.orchestrator.execution_loop_delay)
                continue

            # Match tasks to agents
            assignments = []
            if ready_tasks and available_agents:
                assignments = await self._match_tasks_to_agents(ready_tasks, available_agents)

            # Execute newly assigned tasks
            if assignments:
                for task, agent in assignments:
                    # Mark task as started immediately to prevent re-scheduling
                    await self.task_queue.mark_task_started(task.id, agent.agent.id)

                    # Publish started event
                    await self.event_bus.publish(
                        EventTypes.TASK_STARTED,
                        {
                            "task_id": str(task.id),
                            "task_title": task.title,
                            "agent_id": str(agent.agent.id),
                        },
                    )

                    if self.config.orchestrator.enable_parallel_execution:
                        # Schedule execution
                        future = asyncio.create_task(self._execute_task(task, agent))
                        pending_futures.add(future)
                    else:
                        # Execute sequentially
                        await self._execute_task(task, agent)

            # Handle execution flow
            if self.config.orchestrator.enable_parallel_execution and pending_futures:
                # Wait for at least one task to complete to free up an agent
                done, pending_futures = await asyncio.wait(
                    pending_futures,
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Check for exceptions in completed tasks
                for future in done:
                    try:
                        await future
                    except Exception as e:
                        logger.error("Unhandled exception in task future", error=str(e))

            elif not assignments:
                # No assignments and (no pending futures OR sequential mode)
                # Just wait a bit
                await asyncio.sleep(self.config.orchestrator.execution_loop_delay)

            # Progress update
            stats = await self.task_queue.get_stats()
            completed = stats["by_status"].get(TaskStatus.COMPLETED.value, 0)
            failed = stats["by_status"].get(TaskStatus.FAILED.value, 0)
            total = stats["total"]

            await self.event_bus.publish(
                EventTypes.PROGRESS_UPDATE,
                {
                    "completed": completed,
                    "failed": failed,
                    "total": total,
                    "iteration": iteration,
                },
            )

        # Final stats
        final_stats = await self.task_queue.get_stats()
        logger.info("Execution loop completed", iterations=iteration, **final_stats)

    async def _match_tasks_to_agents(
        self, ready_tasks: list[Any], available_agents: list[Any]
    ) -> list[tuple[Any, Any]]:
        """Match ready tasks to available agents.

        Args:
            ready_tasks: List of ready tasks
            available_agents: List of available agents

        Returns:
            List of (task, agent) tuples
        """
        assignments = []

        # Keep track of agents we've assigned
        assigned_agent_ids = set()

        for task in ready_tasks:
            # Find an agent that can handle this task and hasn't been assigned yet
            for agent in available_agents:
                if (
                    agent.agent.can_handle_task(task.type)
                    and str(agent.agent.id) not in assigned_agent_ids
                ):
                    assignments.append((task, agent))
                    assigned_agent_ids.add(str(agent.agent.id))
                    break

        logger.debug("Matched tasks to agents", assignments=len(assignments))
        return assignments

    async def _execute_task(self, task: Any, agent: Any) -> None:
        """Execute a single task on an agent.

        Args:
            task: Task to execute
            agent: Agent to execute on
        """
        try:
            # Note: Task is already marked as started by the caller

            # Execute task
            result = await self.agent_pool.execute_task_on_agent(task, agent)

            # Store result
            self.task_results.append(result)

            # Track cost
            self.cost_tracker.track_usage(
                model=self.config.anthropic.default_model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )

            # Mark task as completed or failed
            if result.status.value == "success":
                await self.task_queue.mark_task_completed(
                    task.id, {"artifacts": len(result.artifacts)}
                )
                await self.event_bus.publish(
                    EventTypes.TASK_COMPLETED,
                    {"task_id": str(task.id), "artifacts": len(result.artifacts)},
                )
            else:
                # Try to retry or mark as failed
                should_retry = await self.task_queue.mark_task_failed(
                    task.id, result.error_message or "Unknown error"
                )
                if should_retry:
                    await self.event_bus.publish(
                        EventTypes.TASK_RETRYING,
                        {
                            "task_id": str(task.id),
                            "retry_count": task.retry_count + 1,
                            "error": result.error_message,
                        },
                    )
                else:
                    await self.event_bus.publish(
                        EventTypes.TASK_FAILED,
                        {"task_id": str(task.id), "error": result.error_message},
                    )

        except Exception as e:
            logger.error("Error executing task", task_id=str(task.id), error=str(e))
            await self.task_queue.mark_task_failed(task.id, str(e))
            await self.event_bus.publish(
                EventTypes.TASK_FAILED, {"task_id": str(task.id), "error": str(e)}
            )
