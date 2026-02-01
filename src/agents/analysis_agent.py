"""Analysis and architecture agent."""

import re

from src.agents.base_agent import BaseAgent
from src.models.result import Artifact, ArtifactType
from src.models.task import Task


class AnalysisAgent(BaseAgent):
    """Agent specialized in software analysis and architecture."""

    def get_system_prompt(self) -> str:
        """Get system prompt for analysis."""
        return """You are an expert software architect and analyst with deep knowledge of system design, architecture patterns, and best practices.

Your responsibilities:
1. Analyze requirements and propose solutions
2. Design system architecture and components
3. Identify potential issues and risks
4. Recommend technologies and approaches
5. Create technical specifications

When performing analysis:
- Consider scalability, performance, and maintainability
- Identify trade-offs between different approaches
- Recommend specific technologies with justification
- Address security and compliance concerns
- Think about deployment and operations

Output your analysis in a structured markdown format with sections:
- Executive Summary
- Requirements Analysis
- Proposed Architecture
- Technology Recommendations
- Risks and Mitigation
- Next Steps

Include diagrams descriptions (system diagrams, flow charts, etc.) where relevant."""

    async def process_task(self, task: Task, response: str) -> list[Artifact]:
        """Extract analysis artifacts from response.

        Args:
            task: Task being executed
            response: Claude's response

        Returns:
            List of analysis artifacts
        """
        # Check for multiple analysis documents
        sections = self._split_analysis_sections(response)

        artifacts = []
        for i, (section_name, content) in enumerate(sections):
            artifact = Artifact(
                type=ArtifactType.ANALYSIS,
                name=section_name or f"{task.title} - Analysis {i + 1}",
                content=content.strip(),
                language="markdown",
                file_path=self._get_file_path(section_name, i),
                metadata={
                    "task_id": str(task.id),
                    "task_title": task.title,
                },
            )
            artifacts.append(artifact)

        return artifacts

    def _split_analysis_sections(self, response: str) -> list[tuple[str | None, str]]:
        """Split response into analysis sections.

        Args:
            response: Full response text

        Returns:
            List of (section_name, content) tuples
        """
        # Look for section markers
        section_pattern = r"#\s*Analysis:\s*(.+?)\n(.*?)(?=\n#\s*Analysis:|$)"
        matches = re.findall(section_pattern, response, re.DOTALL)

        if matches:
            return [(name.strip(), content) for name, content in matches]
        else:
            # Single analysis document
            return [(None, response)]

    def _get_file_path(self, section_name: str | None, index: int) -> str:
        """Get file path for analysis document.

        Args:
            section_name: Section name
            index: Section index

        Returns:
            File path
        """
        if section_name:
            # Sanitize name for file path
            name = re.sub(r"[^\w\s-]", "", section_name.lower())
            name = re.sub(r"[\s]+", "_", name)
            return f"analysis_{name}.md"
        else:
            return f"analysis_{index + 1}.md"
