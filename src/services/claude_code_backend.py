"""Claude Code backend for executing tasks using Claude Code instead of API."""

import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import aiofiles
from anthropic.types import Usage

from src.utils.logger import get_logger
from src.utils.errors import APIError

logger = get_logger(__name__)


class ClaudeCodeBackend:
    """Backend that uses Claude Code CLI instead of Anthropic API."""

    def __init__(self) -> None:
        """Initialize Claude Code backend."""
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._check_claude_code_available()

    def _check_claude_code_available(self) -> None:
        """Check if Claude Code CLI is available."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info("Claude Code CLI detected", version=result.stdout.strip())
            else:
                logger.warning("Claude Code CLI not found, will use embedded mode")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning("Claude Code CLI not available, using embedded mode")

    async def create_message(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage]:
        """Create a message using Claude Code.

        Args:
            system: System prompt
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (ignored, uses Claude Code's model)
            max_tokens: Maximum tokens (ignored)
            temperature: Sampling temperature (ignored)
            **kwargs: Additional API parameters (ignored)

        Returns:
            Tuple of (response text, usage stats)

        Raises:
            APIError: If execution fails
        """
        try:
            # Try CLI first, fall back to embedded mode
            response_text = await self._execute_via_cli(system, messages)
            if not response_text:
                response_text = await self._execute_embedded(system, messages)

            # Estimate token usage (rough approximation)
            input_text = system + "\n".join(m["content"] for m in messages)
            input_tokens = len(input_text) // 4
            output_tokens = len(response_text) // 4

            self._total_input_tokens += input_tokens
            self._total_output_tokens += output_tokens

            # Create usage object
            usage = Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            logger.info(
                "Claude Code execution complete",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            return response_text, usage

        except Exception as e:
            logger.error("Claude Code execution failed", error=str(e))
            raise APIError(f"Claude Code backend error: {e}")

    async def _execute_via_cli(
        self, system: str, messages: list[dict[str, str]]
    ) -> str | None:
        """Execute via Claude Code CLI if available.

        Args:
            system: System prompt
            messages: Messages

        Returns:
            Response text or None if CLI not available
        """
        try:
            # Create a temporary file with the prompt
            fd, prompt_file = tempfile.mkstemp(suffix='.md', text=True)
            os.close(fd)

            # Write the full prompt
            async with aiofiles.open(prompt_file, mode='w', encoding='utf-8') as f:
                await f.write(f"# System Instructions\n\n{system}\n\n")
                await f.write("# Task\n\n")
                for msg in messages:
                    if msg["role"] == "user":
                        await f.write(msg["content"])
                        await f.write("\n\n")

            # Execute Claude Code CLI
            result = await asyncio.create_subprocess_exec(
                "claude",
                prompt_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            # Clean up temp file
            Path(prompt_file).unlink(missing_ok=True)

            if result.returncode == 0:
                return stdout.decode('utf-8').strip()
            else:
                logger.warning("Claude CLI execution failed", error=stderr.decode('utf-8'))
                return None

        except FileNotFoundError:
            # Claude CLI not installed
            return None
        except Exception as e:
            logger.warning("Claude CLI execution error", error=str(e))
            return None

    async def _execute_embedded(
        self, system: str, messages: list[dict[str, str]]
    ) -> str:
        """Execute in embedded mode (within this Claude Code session).

        This creates a structured output file that can be picked up.

        Args:
            system: System prompt
            messages: Messages

        Returns:
            Response text
        """
        # Create a marker file for the current session
        task_id = f"task_{asyncio.get_event_loop().time()}"

        # Build the full prompt
        full_prompt = f"""# System Instructions

{system}

# Task

"""
        for msg in messages:
            if msg["role"] == "user":
                full_prompt += msg["content"] + "\n\n"

        # Save to a temporary request file
        request_dir = Path("./temp_claude_code_requests")
        request_dir.mkdir(exist_ok=True)

        request_file = request_dir / f"{task_id}_request.md"
        response_file = request_dir / f"{task_id}_response.md"

        # Write request
        async with aiofiles.open(request_file, 'w', encoding='utf-8') as f:
            await f.write(full_prompt)

        # Create instruction file for user
        instruction = f"""
⚠️  CLAUDE CODE INTEGRATION MODE ⚠️

A task is waiting for Claude Code execution.

REQUEST FILE: {request_file}
RESPONSE FILE: {response_file}

Please read the request file and write your response to the response file.

You can do this by:
1. Read the request: {request_file}
2. Complete the task
3. Write response to: {response_file}

Or simply execute:
---
Read the task from: {request_file}
Then write your complete response to: {response_file}
---

Waiting for response file to be created...
"""

        print(instruction)
        logger.info("Waiting for Claude Code response",
                   request=str(request_file),
                   response=str(response_file))

        # Wait for response file (with timeout)
        max_wait = 300  # 5 minutes
        wait_interval = 2
        total_waited = 0

        while total_waited < max_wait:
            if response_file.exists():
                # Read response
                async with aiofiles.open(response_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    response = content.strip()

                if response:
                    # Clean up
                    request_file.unlink(missing_ok=True)
                    response_file.unlink(missing_ok=True)
                    return response

            await asyncio.sleep(wait_interval)
            total_waited += wait_interval

        raise APIError("Timeout waiting for Claude Code response")

    async def create_message_stream(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage]:
        """Create a streaming message (delegates to regular create_message).

        Args:
            system: System prompt
            messages: Messages
            model: Model (ignored)
            max_tokens: Max tokens (ignored)
            temperature: Temperature (ignored)
            **kwargs: Additional parameters

        Returns:
            Response and usage
        """
        return await self.create_message(
            system=system,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    def get_total_tokens(self) -> dict[str, int]:
        """Get total token usage.

        Returns:
            Dictionary with token counts
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
