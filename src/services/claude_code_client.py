"""Simplified Claude Code client that works within a Claude Code session."""

import asyncio
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
from anthropic.types import Usage

from src.utils.logger import get_logger
from src.utils.errors import APIError

logger = get_logger(__name__)


class ClaudeCodeClient:
    """Client that uses Claude Code session instead of Anthropic API.

    This is designed to work within an active Claude Code session by creating
    task files that can be executed interactively.
    """

    def __init__(self, work_dir: Path | None = None):
        """Initialize Claude Code client.

        Args:
            work_dir: Working directory for task files (default: ./claude_code_tasks)
        """
        self.work_dir = work_dir or Path("./claude_code_tasks")
        self.work_dir.mkdir(exist_ok=True)
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._task_counter = 0

        logger.info("Claude Code client initialized", work_dir=str(self.work_dir))

    async def create_message(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage]:
        """Create a message by having user execute it in Claude Code.

        Args:
            system: System prompt
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (informational only)
            max_tokens: Maximum tokens (informational only)
            temperature: Sampling temperature (informational only)
            **kwargs: Additional parameters

        Returns:
            Tuple of (response text, usage stats)
        """
        self._task_counter += 1
        task_id = f"task_{self._task_counter:03d}"

        # Extract user message
        user_content = "\n\n".join(m["content"] for m in messages if m["role"] == "user")

        # Create task file with clear instructions
        task_file = self.work_dir / f"{task_id}_prompt.md"
        response_file = self.work_dir / f"{task_id}_response.md"

        task_content = f"""# Task {task_id}

## System Instructions

{system}

## Your Task

{user_content}

## Instructions

Please provide your response and save it to: `{response_file}`

Your response should be complete and ready to use.
"""

        # Write task file
        async with aiofiles.open(task_file, 'w', encoding='utf-8') as f:
            await f.write(task_content)

        # Display instructions to user
        print("\n" + "="*60)
        print(f"📋 TASK {task_id} - Claude Code Execution Required")
        print("="*60)
        print(f"\nTask file created: {task_file}")
        print(f"Response file: {response_file}")
        print("\nPlease execute this task and save the response.")
        print("\nWaiting for response file...")
        print("="*60 + "\n")

        # Wait for response file
        response = await self._wait_for_response(response_file, timeout=600)

        # Estimate tokens
        input_tokens = (len(system) + len(user_content)) // 4
        output_tokens = len(response) // 4

        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        usage = Usage(input_tokens=input_tokens, output_tokens=output_tokens)

        logger.info(
            "Task completed",
            task_id=task_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        return response, usage

    async def _wait_for_response(self, response_file: Path, timeout: int = 600) -> str:
        """Wait for response file to be created.

        Args:
            response_file: Path to response file
            timeout: Maximum wait time in seconds

        Returns:
            Response content

        Raises:
            APIError: If timeout or file not found
        """
        wait_interval = 2
        total_waited = 0

        while total_waited < timeout:
            if await aiofiles.os.path.exists(response_file):
                try:
                    async with aiofiles.open(response_file, 'r', encoding='utf-8') as f:
                        content = (await f.read()).strip()

                    if content:
                        logger.info("Response received", file=str(response_file))
                        return content
                except Exception as e:
                    logger.warning("Error reading response file", error=str(e))

            await asyncio.sleep(wait_interval)
            total_waited += wait_interval

            # Show progress every 30 seconds
            if total_waited % 30 == 0:
                print(f"⏳ Still waiting for response... ({total_waited}s elapsed)")

        raise APIError(f"Timeout waiting for response file: {response_file}")

    def get_total_tokens(self) -> dict[str, int]:
        """Get total token usage.

        Returns:
            Dictionary with token counts (estimates)
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
