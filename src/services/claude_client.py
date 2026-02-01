"""Claude API client wrapper."""

import asyncio
from typing import Any

import anthropic
from anthropic.types import Message, Usage

from src.models.config import AnthropicConfig
from src.utils.errors import APIError
from src.utils.logger import get_logger
from src.utils.retry import retry_on_api_error

logger = get_logger(__name__)


class ClaudeClient:
    """Wrapper for Anthropic API client with error handling and retries."""

    def __init__(self, config: AnthropicConfig):
        """Initialize Claude client.

        Args:
            config: Anthropic API configuration
        """
        self.config = config
        self.client = anthropic.AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
        )
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @retry_on_api_error(max_attempts=3)
    async def create_message(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage]:
        """Create a message using Claude API.

        Args:
            system: System prompt
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to config default)
            max_tokens: Maximum tokens (defaults to config default)
            temperature: Sampling temperature (defaults to config default)
            **kwargs: Additional API parameters

        Returns:
            Tuple of (response text, usage stats)

        Raises:
            APIError: If API call fails
        """
        model = model or self.config.default_model
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature

        try:
            logger.info(
                "Creating Claude message",
                model=model,
                max_tokens=max_tokens,
                message_count=len(messages),
            )

            response: Message = await self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,  # type: ignore
                **kwargs,
            )

            # Extract text content
            text_content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_content += block.text

            # Track token usage
            usage = response.usage
            self._total_input_tokens += usage.input_tokens
            self._total_output_tokens += usage.output_tokens

            logger.info(
                "Claude message created",
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )

            return text_content, usage

        except anthropic.APIError as e:
            logger.error("Claude API error", error=str(e), status_code=getattr(e, "status_code", None))
            raise APIError(str(e), status_code=getattr(e, "status_code", None))
        except Exception as e:
            logger.error("Unexpected error calling Claude API", error=str(e))
            raise APIError(f"Unexpected error: {e}")

    async def create_message_stream(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> tuple[str, Usage]:
        """Create a streaming message (for future use).

        Currently collects the full response. Can be enhanced for true streaming.

        Args:
            system: System prompt
            messages: List of message dicts
            model: Model to use
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Tuple of (response text, usage stats)
        """
        # For now, just use the regular create_message
        # Can be enhanced later with actual streaming
        return await self.create_message(
            system=system,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

    def get_total_tokens(self) -> dict[str, int]:
        """Get total token usage across all calls.

        Returns:
            Dictionary with input, output, and total token counts
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
