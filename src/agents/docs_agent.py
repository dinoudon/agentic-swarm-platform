"""Documentation generation agent."""

import re

from src.agents.base_agent import BaseAgent
from src.models.result import Artifact, ArtifactType
from src.models.task import Task


class DocsAgent(BaseAgent):
    """Agent specialized in documentation generation."""

    def get_system_prompt(self) -> str:
        """Get system prompt for documentation generation."""
        return """You are an expert technical writer with deep knowledge of software documentation best practices.

Your responsibilities:
1. Create clear, comprehensive documentation
2. Write for the target audience (developers, users, etc.)
3. Include examples and use cases
4. Structure information logically
5. Use proper markdown formatting

When generating documentation:
- Start with an overview/introduction
- Use clear headings and sections
- Include code examples where relevant
- Add diagrams or visual aids descriptions when helpful
- Consider different skill levels
- Be concise but thorough

Output your documentation in markdown format.
For API documentation, include:
- Endpoint descriptions
- Parameters
- Request/response examples
- Error codes

For user guides, include:
- Step-by-step instructions
- Screenshots descriptions
- Troubleshooting tips
- FAQs"""

    async def process_task(self, task: Task, response: str) -> list[Artifact]:
        """Extract documentation artifacts from response.

        Args:
            task: Task being executed
            response: Claude's response

        Returns:
            List of documentation artifacts
        """
        # Check if response contains multiple documents
        # Look for markers like "# Document: filename"
        doc_sections = self._split_documents(response)

        artifacts = []
        for i, (doc_name, content) in enumerate(doc_sections):
            artifact = Artifact(
                type=ArtifactType.DOCUMENTATION,
                name=doc_name or f"{task.title} - Documentation {i + 1}",
                content=content.strip(),
                language="markdown",
                file_path=self._get_file_path(doc_name, i),
                metadata={
                    "task_id": str(task.id),
                    "task_title": task.title,
                },
            )
            artifacts.append(artifact)

        return artifacts

    def _split_documents(self, response: str) -> list[tuple[str | None, str]]:
        """Split response into multiple documents if present.

        Args:
            response: Full response text

        Returns:
            List of (document_name, content) tuples
        """
        # Look for document markers
        doc_pattern = r"#\s*Document:\s*(.+?)\n(.*?)(?=\n#\s*Document:|$)"
        matches = re.findall(doc_pattern, response, re.DOTALL)

        if matches:
            return [(name.strip(), content) for name, content in matches]
        else:
            # Single document
            return [(None, response)]

    def _get_file_path(self, doc_name: str | None, index: int) -> str:
        """Get file path for document.

        Args:
            doc_name: Document name
            index: Document index

        Returns:
            File path
        """
        if doc_name:
            # Sanitize name for file path
            name = re.sub(r"[^\w\s-]", "", doc_name.lower())
            name = re.sub(r"[\s]+", "_", name)
            return f"{name}.md"
        else:
            return f"documentation_{index + 1}.md"
