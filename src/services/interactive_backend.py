"""Interactive backend for Claude Code - executes tasks one at a time with user help."""

import asyncio
from pathlib import Path
from typing import Any

from anthropic.types import Usage

from src.utils.logger import get_logger

logger = get_logger(__name__)


class InteractiveBackend:
    """Interactive backend that prompts user to execute tasks.

    This is perfect for Claude Code users without API keys.
    Tasks are displayed and user can ask Claude Code to execute them.
    """

    def __init__(self):
        """Initialize interactive backend."""
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self.task_count = 0

        # Create output directory for task tracking
        self.output_dir = Path("./interactive_tasks")
        self.output_dir.mkdir(exist_ok=True)

        print("\n" + "="*70)
        print("🤖 INTERACTIVE MODE - Using Claude Code")
        print("="*70)
        print("Tasks will be displayed for you to execute with Claude Code.")
        print("You can copy the prompts and ask Claude Code to complete them.")
        print("="*70 + "\n")

    async def create_message(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage]:
        """Create a message interactively.

        Displays the task and waits for user to provide response.

        Args:
            system: System prompt
            messages: Messages
            model: Model (not used)
            max_tokens: Max tokens (not used)
            temperature: Temperature (not used)
            **kwargs: Additional parameters

        Returns:
            Response text and usage estimate
        """
        self.task_count += 1

        # Extract user message
        user_content = "\n\n".join(m["content"] for m in messages if m["role"] == "user")

        # Create task file for reference
        task_file = self.output_dir / f"task_{self.task_count:03d}.md"

        task_content = f"""# Task {self.task_count}

## System Instructions

{system}

## Task Description

{user_content}

---

## How to Execute

1. Read the system instructions above
2. Complete the task described
3. Provide your complete response below

## Response

[Paste your response here]
"""

        # Save task file
        with open(task_file, 'w', encoding='utf-8') as f:
            f.write(task_content)

        # Display to console
        print("\n" + "="*70)
        print(f"📝 TASK #{self.task_count}")
        print("="*70)
        print("\n📌 SYSTEM INSTRUCTIONS:")
        print("-" * 70)
        print(system)
        print("\n📌 TASK:")
        print("-" * 70)
        print(user_content)
        print("\n" + "="*70)
        print(f"Task saved to: {task_file}")
        print("\n💡 You can now:")
        print("  1. Copy the task above")
        print("  2. Ask Claude Code to complete it")
        print("  3. Copy the response")
        print("  4. Paste it in the response file")
        print("="*70 + "\n")

        # Wait for response file
        response_file = self.output_dir / f"task_{self.task_count:03d}_response.txt"

        print(f"⏳ Waiting for response file: {response_file}")
        print("   Create this file and paste the response when ready.\n")

        response = await self._wait_for_file(response_file)

        # Estimate tokens
        input_tokens = (len(system) + len(user_content)) // 4
        output_tokens = len(response) // 4

        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens)

        print(f"✅ Task #{self.task_count} completed!\n")

        return response, usage

    async def _wait_for_file(self, file_path: Path, timeout: int = 1800) -> str:
        """Wait for a file to be created and return its contents.

        Args:
            file_path: Path to wait for
            timeout: Maximum wait time in seconds

        Returns:
            File contents

        Raises:
            TimeoutError: If file not created in time
        """
        elapsed = 0
        check_interval = 3

        while elapsed < timeout:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()

                    if content:  # File exists and has content
                        return content
                except Exception as e:
                    logger.warning(f"Error reading file: {e}")

            await asyncio.sleep(check_interval)
            elapsed += check_interval

            # Progress indicator every 30 seconds
            if elapsed % 30 == 0 and elapsed < timeout:
                print(f"⏳ Still waiting... ({elapsed}s / {timeout}s)")

        raise TimeoutError(f"Timeout waiting for file: {file_path}")

    def get_total_tokens(self) -> dict[str, int]:
        """Get total token usage estimate.

        Returns:
            Token usage dictionary
        """
        return {
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
        }

    def reset_token_counts(self) -> None:
        """Reset token counters."""
        self._total_input_tokens = 0
        self._total_output_tokens = 0
