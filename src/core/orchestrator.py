"""Main orchestrator for coordinating PRD execution."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

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

        # Task execution tracking
        self.running_tasks: set[asyncio.Task] = set()
        self.processing_task_ids: set[UUID] = set()
        self.processing_agent_ids: set[UUID] = set()

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
        max_iterations = 100000  # Safety limit

        while not await self.task_queue.is_complete() and iteration < max_iterations:
            # Check if we should increment iteration (only if we did work or waited)
            did_work = False

            # Get ready tasks and available agents
            ready_tasks = await self.task_queue.get_ready_tasks()
            available_agents = await self.agent_pool.get_available_agents()

            # Filter out tasks/agents currently being processed (async gap protection)
            ready_tasks = [
                t for t in ready_tasks if t.id not in self.processing_task_ids
            ]
            available_agents = [
                a
                for a in available_agents
                if a.agent.id not in self.processing_agent_ids
            ]

            if not ready_tasks:
                # No ready tasks, check if we're truly done or just waiting
                stats = await self.task_queue.get_stats()
                in_progress = stats["by_status"].get(TaskStatus.IN_PROGRESS.value, 0)

                # Also check our local running tasks
                local_running = len(self.running_tasks)

                if in_progress == 0 and local_running == 0:
                    # No tasks ready and none in progress - we're stuck or done
                    break

                # Tasks in progress, wait a bit
                await asyncio.sleep(self.config.orchestrator.execution_loop_delay)
                iteration += 1
                continue

            if not available_agents:
                # No available agents, wait for some to become free
                await asyncio.sleep(self.config.orchestrator.execution_loop_delay)
                iteration += 1
                continue

            # Match tasks to agents
            assignments = await self._match_tasks_to_agents(ready_tasks, available_agents)

            if not assignments:
                # Couldn't match any tasks to agents
                await asyncio.sleep(self.config.orchestrator.execution_loop_delay)
                iteration += 1
                continue

            # Execute tasks in parallel
            if self.config.orchestrator.enable_parallel_execution:
                # Execute all assignments concurrently without blocking
                for task, agent in assignments:
                    # Mark as processing to prevent re-assignment during async setup
                    self.processing_task_ids.add(task.id)
                    self.processing_agent_ids.add(agent.agent.id)

                    # Create background task
                    task_coro = self._execute_task_safe(task, agent)
                    async_task = asyncio.create_task(task_coro)

                    # Track running task
                    self.running_tasks.add(async_task)
                    async_task.add_done_callback(self.running_tasks.discard)

                did_work = True
            else:
                # Execute sequentially
                for task, agent in assignments:
                    await self._execute_task(task, agent)
                did_work = True

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

            # Only increment iteration if we did work or explicitly waited above
            if did_work:
                iteration += 1

            # Small delay between iterations to yield control
            await asyncio.sleep(self.config.orchestrator.execution_loop_delay)

        # Wait for any remaining tasks to complete
        if self.running_tasks:
            logger.info("Waiting for remaining tasks to complete", count=len(self.running_tasks))
            await asyncio.gather(*self.running_tasks, return_exceptions=True)

        # Final stats
        final_stats = await self.task_queue.get_stats()
        logger.info("Execution loop completed", iterations=iteration, **final_stats)

    async def _execute_task_safe(self, task: Any, agent: Any) -> None:
        """Execute a task with cleanup of processing state.

        Args:
            task: Task to execute
            agent: Agent to execute on
        """
        try:
            await self._execute_task(task, agent)
        except Exception as e:
            logger.critical("Unhandled exception in task execution", task_id=str(task.id), error=str(e))
        finally:
            # Cleanup processing state
            self.processing_task_ids.discard(task.id)
            self.processing_agent_ids.discard(agent.agent.id)

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
            # Mark task as started
            await self.task_queue.mark_task_started(task.id, agent.agent.id)

            # Publish task started event
            await self.event_bus.publish(
                EventTypes.TASK_STARTED,
                {
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "agent_id": str(agent.agent.id),
                },
            )

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
