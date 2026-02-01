"""Agent pool manager for creating and managing agents."""

import asyncio
from typing import Any
from uuid import uuid4

from src.agents.analysis_agent import AnalysisAgent
from src.agents.base_agent import BaseAgent
from src.agents.code_agent import CodeAgent
from src.agents.docs_agent import DocsAgent
from src.agents.test_agent import TestAgent
from src.models.agent import Agent, AgentCapability, AgentStatus, AgentType
from src.models.config import AgentPoolConfig
from src.models.result import TaskResult
from src.models.task import Task, TaskType
from src.services.claude_client import ClaudeClient
from src.services.rate_limiter import RateLimiter
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentPool:
    """Manages a pool of specialized agents."""

    def __init__(
        self,
        config: AgentPoolConfig,
        claude_client: ClaudeClient,
        rate_limiter: RateLimiter,
    ):
        """Initialize agent pool.

        Args:
            config: Agent pool configuration
            claude_client: Claude API client
            rate_limiter: Rate limiter
        """
        self.config = config
        self.claude_client = claude_client
        self.rate_limiter = rate_limiter
        self.agents: dict[str, BaseAgent] = {}
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the agent pool with configured agents."""
        logger.info("Initializing agent pool", max_agents=self.config.max_agents)

        # Create code generation agents
        for i in range(self.config.code_agent_count):
            await self._create_agent(AgentType.CODE_GENERATOR, f"code-agent-{i + 1}")

        # Create documentation agents
        for i in range(self.config.docs_agent_count):
            await self._create_agent(AgentType.DOCUMENTATION, f"docs-agent-{i + 1}")

        # Create analysis agents
        for i in range(self.config.analysis_agent_count):
            await self._create_agent(AgentType.ANALYSIS, f"analysis-agent-{i + 1}")

        # Create test agents
        for i in range(self.config.test_agent_count):
            await self._create_agent(AgentType.TESTING, f"test-agent-{i + 1}")

        logger.info("Agent pool initialized", agent_count=len(self.agents))

    async def _create_agent(self, agent_type: AgentType, name: str) -> BaseAgent:
        """Create an agent of the specified type.

        Args:
            agent_type: Type of agent to create
            name: Agent name/identifier

        Returns:
            Created agent instance
        """
        # Define capabilities based on type
        capabilities = self._get_capabilities(agent_type)

        # Create agent model
        agent_model = Agent(
            id=uuid4(),
            type=agent_type,
            capabilities=capabilities,
            status=AgentStatus.IDLE,
        )

        # Create specialized agent instance
        if agent_type == AgentType.CODE_GENERATOR:
            agent = CodeAgent(agent_model, self.claude_client, self.rate_limiter)
        elif agent_type == AgentType.DOCUMENTATION:
            agent = DocsAgent(agent_model, self.claude_client, self.rate_limiter)
        elif agent_type == AgentType.ANALYSIS:
            agent = AnalysisAgent(agent_model, self.claude_client, self.rate_limiter)
        elif agent_type == AgentType.TESTING:
            agent = TestAgent(agent_model, self.claude_client, self.rate_limiter)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        # Add to pool
        async with self._lock:
            self.agents[str(agent_model.id)] = agent

        logger.debug("Agent created", agent_id=str(agent_model.id), type=agent_type.value)
        return agent

    def _get_capabilities(self, agent_type: AgentType) -> AgentCapability:
        """Get capabilities for an agent type.

        Args:
            agent_type: Agent type

        Returns:
            Agent capabilities
        """
        capability_map = {
            AgentType.CODE_GENERATOR: AgentCapability(
                task_types=[TaskType.CODE_GENERATION],
                max_concurrent_tasks=1,
                specializations=["code_generation", "programming"],
            ),
            AgentType.DOCUMENTATION: AgentCapability(
                task_types=[TaskType.DOCUMENTATION],
                max_concurrent_tasks=1,
                specializations=["documentation", "technical_writing"],
            ),
            AgentType.ANALYSIS: AgentCapability(
                task_types=[TaskType.ANALYSIS],
                max_concurrent_tasks=1,
                specializations=["architecture", "analysis", "design"],
            ),
            AgentType.TESTING: AgentCapability(
                task_types=[TaskType.TESTING],
                max_concurrent_tasks=1,
                specializations=["testing", "qa", "test_automation"],
            ),
        }
        return capability_map[agent_type]

    async def get_available_agents(self) -> list[BaseAgent]:
        """Get agents that are available to take tasks.

        Returns:
            List of available agents
        """
        async with self._lock:
            return [agent for agent in self.agents.values() if agent.agent.is_available()]

    async def get_agent_for_task(self, task: Task) -> BaseAgent | None:
        """Get best available agent for a task.

        Args:
            task: Task to assign

        Returns:
            Agent if available, None otherwise
        """
        async with self._lock:
            # Filter agents that can handle this task type
            capable_agents = [
                agent
                for agent in self.agents.values()
                if agent.agent.can_handle_task(task.type) and agent.agent.is_available()
            ]

            if not capable_agents:
                return None

            # Pick agent with best performance (lowest average task duration)
            # or least busy if no history yet
            best_agent = min(
                capable_agents,
                key=lambda a: (
                    a.agent.metrics.average_task_duration
                    if a.agent.metrics.tasks_completed > 0
                    else 0.0,
                    len(a.agent.task_queue),
                ),
            )

            return best_agent

    async def assign_task(self, task: Task, agent: BaseAgent) -> None:
        """Assign a task to an agent.

        Args:
            task: Task to assign
            agent: Agent to assign to
        """
        async with self._lock:
            agent.agent.assign_task(task.id)
            logger.debug(
                "Task assigned to agent",
                task_id=str(task.id),
                agent_id=str(agent.agent.id),
                agent_type=agent.agent.type.value,
            )

    async def execute_task_on_agent(self, task: Task, agent: BaseAgent) -> TaskResult:
        """Execute a task on a specific agent.

        Args:
            task: Task to execute
            agent: Agent to execute on

        Returns:
            Task result
        """
        return await agent.execute_task(task)

    async def get_stats(self) -> dict[str, Any]:
        """Get agent pool statistics.

        Returns:
            Dictionary with pool stats
        """
        async with self._lock:
            total_agents = len(self.agents)
            available = sum(1 for a in self.agents.values() if a.agent.is_available())
            busy = sum(1 for a in self.agents.values() if a.agent.status == AgentStatus.BUSY)

            total_completed = sum(a.agent.metrics.tasks_completed for a in self.agents.values())
            total_failed = sum(a.agent.metrics.tasks_failed for a in self.agents.values())

            return {
                "total_agents": total_agents,
                "available": available,
                "busy": busy,
                "total_tasks_completed": total_completed,
                "total_tasks_failed": total_failed,
            }

    async def shutdown(self) -> None:
        """Shutdown all agents."""
        async with self._lock:
            for agent in self.agents.values():
                agent.agent.status = AgentStatus.SHUTDOWN
            logger.info("Agent pool shutdown", agent_count=len(self.agents))
