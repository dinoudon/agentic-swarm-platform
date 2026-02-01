"""PRD parser and task slicer using Claude."""

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiofiles

from src.models.prd import PRD, PRDMetadata, PRDSection
from src.models.task import Task, TaskComplexity, TaskDependencyGraph, TaskPriority, TaskType
from src.services.claude_client import ClaudeClient
from src.utils.errors import PRDParseError
from src.utils.logger import get_logger

logger = get_logger(__name__)


TASK_SLICING_SYSTEM_PROMPT = """You are an expert project manager analyzing a Product Requirements Document (PRD).
Your task is to break down the PRD into specific, actionable tasks that can be executed in parallel by specialized AI agents.

For each task, provide:
- type: one of ["code_generation", "documentation", "analysis", "testing"]
- title: brief, clear description (max 100 chars)
- description: detailed requirements and acceptance criteria
- priority: one of ["critical", "high", "medium", "low"]
- dependencies: list of task titles this depends on (if any)
- complexity: one of ["small", "medium", "large"]

Guidelines:
1. Make tasks granular enough to be executed independently
2. Identify clear dependencies (e.g., "write tests" depends on "generate code")
3. Group related functionality together
4. Consider the natural workflow (analysis → code → tests → docs)
5. Balance task complexity (avoid tasks that are too large or too small)
6. Ensure test tasks depend on their corresponding code generation tasks
7. Documentation can often be done in parallel with code

Output Format:
Return a valid JSON array of task objects. Each object must have all the fields listed above.

Example:
[
  {
    "type": "analysis",
    "title": "Analyze authentication requirements",
    "description": "Review PRD and analyze authentication flow, security requirements, and integration points",
    "priority": "critical",
    "dependencies": [],
    "complexity": "medium"
  },
  {
    "type": "code_generation",
    "title": "Implement user authentication service",
    "description": "Create authentication service with login, logout, and token validation. Include JWT handling and secure password hashing.",
    "priority": "critical",
    "dependencies": ["Analyze authentication requirements"],
    "complexity": "large"
  }
]"""


class PRDParser:
    """Parses PRD documents and slices them into tasks."""

    def __init__(self, claude_client: ClaudeClient):
        """Initialize PRD parser.

        Args:
            claude_client: Claude API client for task slicing
        """
        self.claude_client = claude_client

    async def parse_file(self, file_path: Path) -> PRD:
        """Parse a PRD from a markdown file.

        Args:
            file_path: Path to PRD markdown file

        Returns:
            Parsed PRD object

        Raises:
            PRDParseError: If parsing fails
        """
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            return await self.parse_content(content, file_path.stem)
        except Exception as e:
            raise PRDParseError(f"Failed to parse PRD file {file_path}: {e}")

    async def parse_content(self, content: str, title: str = "Untitled PRD") -> PRD:
        """Parse PRD from raw markdown content.

        Args:
            content: Raw markdown content
            title: Document title

        Returns:
            Parsed PRD object
        """
        # Extract metadata from front matter if present
        metadata = self._extract_metadata(content, title)

        # Parse sections from markdown
        sections = self._parse_sections(content)

        return PRD(metadata=metadata, sections=sections, raw_content=content)

    def _extract_metadata(self, content: str, default_title: str) -> PRDMetadata:
        """Extract metadata from document.

        Args:
            content: Raw content
            default_title: Default title if not found

        Returns:
            PRD metadata
        """
        # Try to find title from first h1 heading
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else default_title

        # Look for metadata markers
        version_match = re.search(r"Version:\s*(.+)", content, re.IGNORECASE)
        author_match = re.search(r"Author:\s*(.+)", content, re.IGNORECASE)
        tags_match = re.search(r"Tags:\s*(.+)", content, re.IGNORECASE)

        version = version_match.group(1).strip() if version_match else "1.0"
        author = author_match.group(1).strip() if author_match else None
        tags = [t.strip() for t in tags_match.group(1).split(",")] if tags_match else []

        return PRDMetadata(title=title, version=version, author=author, tags=tags)

    def _parse_sections(self, content: str) -> list[PRDSection]:
        """Parse sections from markdown content.

        Args:
            content: Raw markdown content

        Returns:
            List of PRD sections
        """
        sections = []
        lines = content.split("\n")
        current_section: PRDSection | None = None
        current_content: list[str] = []

        for line in lines:
            # Check for heading
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                # Save previous section
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                current_section = PRDSection(title=title, level=level)
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)

        return sections

    async def slice_into_tasks(self, prd: PRD) -> TaskDependencyGraph:
        """Slice PRD into executable tasks using Claude.

        Args:
            prd: Parsed PRD document

        Returns:
            Task dependency graph

        Raises:
            PRDParseError: If task slicing fails
        """
        logger.info("Slicing PRD into tasks", title=prd.metadata.title)

        # Build prompt with PRD content
        user_prompt = f"""Please analyze the following PRD and break it down into actionable tasks.

# PRD: {prd.metadata.title}

{prd.get_full_text()}

---

Break this PRD down into specific tasks. Return a JSON array of task objects as specified."""

        try:
            # Call Claude to slice tasks
            response, usage = await self.claude_client.create_message(
                system=TASK_SLICING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.5,  # Lower temperature for more structured output
            )

            # Extract JSON from response
            tasks_data = self._extract_json_from_response(response)

            # Convert to Task objects
            task_graph = self._build_task_graph(tasks_data)

            # Validate no circular dependencies
            task_graph.validate_no_cycles()

            logger.info(
                "PRD sliced into tasks",
                task_count=len(task_graph.tasks),
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )

            return task_graph

        except Exception as e:
            raise PRDParseError(f"Failed to slice PRD into tasks: {e}")

    def _extract_json_from_response(self, response: str) -> list[dict[str, Any]]:
        """Extract JSON array from Claude's response.

        Args:
            response: Claude's response text

        Returns:
            List of task dictionaries

        Raises:
            PRDParseError: If JSON extraction fails
        """
        # Try to find JSON array in response
        # Look for content between ```json and ``` or just find [ ... ]
        json_match = re.search(r"```json\s*(\[.*?\])\s*```", response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON array
            json_match = re.search(r"(\[.*\])", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                raise PRDParseError("Could not find JSON array in response")

        try:
            tasks_data = json.loads(json_str)
            if not isinstance(tasks_data, list):
                raise PRDParseError("Response is not a JSON array")
            return tasks_data
        except json.JSONDecodeError as e:
            raise PRDParseError(f"Invalid JSON in response: {e}")

    def _build_task_graph(self, tasks_data: list[dict[str, Any]]) -> TaskDependencyGraph:
        """Build task dependency graph from task data.

        Args:
            tasks_data: List of task dictionaries

        Returns:
            Task dependency graph
        """
        # First pass: create all tasks
        task_graph = TaskDependencyGraph()
        title_to_id: dict[str, Any] = {}

        for task_data in tasks_data:
            task = Task(
                id=uuid4(),
                type=TaskType(task_data["type"]),
                title=task_data["title"],
                description=task_data["description"],
                priority=TaskPriority(task_data["priority"]),
                complexity=TaskComplexity(task_data["complexity"]),
            )
            task_graph.add_task(task)
            title_to_id[task.title] = task.id

        # Second pass: resolve dependencies
        for task_data in tasks_data:
            task_title = task_data["title"]
            task_id = title_to_id[task_title]
            task = task_graph.tasks[task_id]

            for dep_title in task_data.get("dependencies", []):
                if dep_title in title_to_id:
                    dep_id = title_to_id[dep_title]
                    task.depends_on.append(dep_id)
                    # Update the dependency's blocks list
                    task_graph.tasks[dep_id].blocks.append(task_id)
                else:
                    logger.warning(
                        "Dependency not found, ignoring",
                        task=task_title,
                        dependency=dep_title,
                    )

        return task_graph
