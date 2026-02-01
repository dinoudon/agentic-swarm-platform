"""Tests for data models."""

import pytest
from datetime import datetime
from uuid import uuid4

from src.models.prd import PRD, PRDMetadata, PRDSection
from src.models.task import Task, TaskType, TaskPriority, TaskStatus, TaskDependencyGraph
from src.models.agent import Agent, AgentType, AgentCapability, AgentStatus


def test_prd_metadata_creation():
    """Test PRD metadata creation."""
    metadata = PRDMetadata(
        title="Test PRD",
        version="1.0",
        author="Test Author",
        tags=["test", "demo"],
    )
    assert metadata.title == "Test PRD"
    assert metadata.version == "1.0"
    assert len(metadata.tags) == 2


def test_prd_section_content():
    """Test PRD section content aggregation."""
    subsection = PRDSection(title="Subsection", content="Subsection content", level=2)
    section = PRDSection(
        title="Main Section", content="Main content", level=1, subsections=[subsection]
    )

    full_content = section.get_all_content()
    assert "Main content" in full_content
    assert "Subsection content" in full_content


def test_task_creation():
    """Test task creation."""
    task = Task(
        type=TaskType.CODE_GENERATION,
        title="Test Task",
        description="Test description",
        priority=TaskPriority.HIGH,
    )

    assert task.type == TaskType.CODE_GENERATION
    assert task.status == TaskStatus.PENDING
    assert task.retry_count == 0


def test_task_is_ready():
    """Test task readiness check."""
    task1 = Task(
        type=TaskType.ANALYSIS, title="Task 1", description="First task", priority=TaskPriority.HIGH
    )
    task2_id = uuid4()
    task2 = Task(
        type=TaskType.CODE_GENERATION,
        title="Task 2",
        description="Second task",
        priority=TaskPriority.MEDIUM,
        depends_on=[task2_id],
    )

    # Task 2 not ready (dependency not completed)
    assert not task2.is_ready(set())

    # Task 2 ready (dependency completed)
    assert task2.is_ready({task2_id})


def test_task_dependency_graph():
    """Test task dependency graph."""
    graph = TaskDependencyGraph()

    task1 = Task(
        type=TaskType.ANALYSIS, title="Task 1", description="First", priority=TaskPriority.HIGH
    )
    task2 = Task(
        type=TaskType.CODE_GENERATION,
        title="Task 2",
        description="Second",
        priority=TaskPriority.MEDIUM,
        depends_on=[task1.id],
    )

    graph.add_task(task1)
    graph.add_task(task2)

    # Task 1 should be ready, Task 2 should not
    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == task1.id

    # Complete Task 1
    graph.mark_task_completed(task1.id, {})

    # Now Task 2 should be ready
    ready = graph.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == task2.id


def test_agent_creation():
    """Test agent creation."""
    capabilities = AgentCapability(
        task_types=[TaskType.CODE_GENERATION], max_concurrent_tasks=1
    )

    agent = Agent(type=AgentType.CODE_GENERATOR, capabilities=capabilities)

    assert agent.type == AgentType.CODE_GENERATOR
    assert agent.status == AgentStatus.IDLE
    assert agent.is_available()


def test_agent_task_assignment():
    """Test agent task assignment."""
    capabilities = AgentCapability(
        task_types=[TaskType.CODE_GENERATION], max_concurrent_tasks=1
    )
    agent = Agent(type=AgentType.CODE_GENERATOR, capabilities=capabilities)

    task_id = uuid4()
    agent.assign_task(task_id)

    assert agent.status == AgentStatus.BUSY
    assert agent.current_task_id == task_id
    assert not agent.is_available()

    agent.complete_current_task()
    assert agent.status == AgentStatus.IDLE
    assert agent.is_available()
