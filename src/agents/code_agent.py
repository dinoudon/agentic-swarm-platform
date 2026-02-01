"""Code generation agent."""

import re
from typing import Any

from src.agents.base_agent import BaseAgent
from src.models.result import Artifact, ArtifactType
from src.models.task import Task


class CodeAgent(BaseAgent):
    """Agent specialized in code generation."""

    def get_system_prompt(self) -> str:
        """Get system prompt for code generation."""
        return """You are an expert software engineer with deep knowledge of multiple programming languages, frameworks, and best practices.

Your responsibilities:
1. Write clean, efficient, and well-documented code
2. Follow industry best practices and design patterns
3. Consider security, performance, and maintainability
4. Include appropriate error handling
5. Write code that is production-ready

When generating code:
- Use clear variable and function names
- Add comments for complex logic
- Follow the language's style conventions
- Include type hints when applicable
- Consider edge cases and error conditions

Output your code in markdown code blocks with the language specified.
Format: ```language
code here
```

If the task requires multiple files, clearly separate them and indicate the file path."""

    async def process_task(self, task: Task, response: str) -> list[Artifact]:
        """Extract code artifacts from response.

        Args:
            task: Task being executed
            response: Claude's response

        Returns:
            List of code artifacts
        """
        artifacts = []

        # Extract code blocks from markdown
        code_blocks = re.findall(r"```(\w+)?\n(.*?)```", response, re.DOTALL)

        for i, (language, code) in enumerate(code_blocks):
            language = language or "text"

            # Try to extract file path from comments or context
            file_path = self._extract_file_path(code, language)
            if not file_path:
                file_path = f"generated_code_{i + 1}.{self._get_extension(language)}"

            artifact = Artifact(
                type=ArtifactType.CODE,
                name=f"{task.title} - {file_path}",
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
        # Look for common file path patterns in comments
        patterns = [
            r"#\s*[Ff]ile:\s*(.+)",  # Python-style: # File: path/to/file.py
            r"//\s*[Ff]ile:\s*(.+)",  # C-style: // File: path/to/file.js
            r"/\*\s*[Ff]ile:\s*(.+?)\s*\*/",  # Block comment: /* File: path */
        ]

        for pattern in patterns:
            match = re.search(pattern, code)
            if match:
                return match.group(1).strip()

        return None

    def _get_extension(self, language: str) -> str:
        """Get file extension for language.

        Args:
            language: Programming language

        Returns:
            File extension
        """
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
            "rust": "rs",
            "go": "go",
            "ruby": "rb",
            "php": "php",
            "swift": "swift",
            "kotlin": "kt",
            "html": "html",
            "css": "css",
            "sql": "sql",
            "bash": "sh",
            "shell": "sh",
        }
        return extensions.get(language.lower(), "txt")
