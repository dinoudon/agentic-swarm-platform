"""Testing agent for test generation."""

import re

from src.agents.base_agent import BaseAgent
from src.models.result import Artifact, ArtifactType
from src.models.task import Task


class TestAgent(BaseAgent):
    """Agent specialized in test generation."""

    def get_system_prompt(self) -> str:
        """Get system prompt for test generation."""
        return """You are an expert QA engineer and test automation specialist with deep knowledge of testing frameworks and best practices.

Your responsibilities:
1. Write comprehensive test suites
2. Cover edge cases and error conditions
3. Follow testing best practices (AAA pattern, etc.)
4. Use appropriate testing frameworks
5. Ensure tests are maintainable and clear

When generating tests:
- Include unit tests for individual functions
- Add integration tests for component interactions
- Cover happy paths and error cases
- Use descriptive test names
- Add assertions with clear messages
- Mock external dependencies
- Aim for high code coverage

Output your tests in markdown code blocks with the language specified.
Include:
- Test setup/fixtures
- Individual test cases
- Teardown if needed
- Comments explaining complex test logic

Use standard testing frameworks:
- Python: pytest, unittest
- JavaScript: Jest, Mocha
- Java: JUnit
- etc."""

    async def process_task(self, task: Task, response: str) -> list[Artifact]:
        """Extract test artifacts from response.

        Args:
            task: Task being executed
            response: Claude's response

        Returns:
            List of test artifacts
        """
        artifacts = []

        # Extract code blocks (tests) from markdown
        code_blocks = re.findall(r"```(\w+)?\n(.*?)```", response, re.DOTALL)

        for i, (language, code) in enumerate(code_blocks):
            language = language or "text"

            # Try to extract file path
            file_path = self._extract_file_path(code, language)
            if not file_path:
                file_path = f"test_{i + 1}.{self._get_extension(language)}"

            artifact = Artifact(
                type=ArtifactType.TEST,
                name=f"{task.title} - Test {i + 1}",
                content=code.strip(),
                language=language,
                file_path=file_path,
                metadata={
                    "task_id": str(task.id),
                    "task_title": task.title,
                },
            )
            artifacts.append(artifact)

        return artifacts

    def _extract_file_path(self, code: str, language: str) -> str | None:
        """Try to extract file path from code comments.

        Args:
            code: Code content
            language: Programming language

        Returns:
            Extracted file path or None
        """
        patterns = [
            r"#\s*[Ff]ile:\s*(.+)",
            r"//\s*[Ff]ile:\s*(.+)",
            r"/\*\s*[Ff]ile:\s*(.+?)\s*\*/",
        ]

        for pattern in patterns:
            match = re.search(pattern, code)
            if match:
                return match.group(1).strip()

        return None

    def _get_extension(self, language: str) -> str:
        """Get file extension for test language.

        Args:
            language: Programming language

        Returns:
            File extension
        """
        # Prefer test_ prefix for test files
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "rust": "rs",
            "go": "go",
        }
        return extensions.get(language.lower(), "txt")
