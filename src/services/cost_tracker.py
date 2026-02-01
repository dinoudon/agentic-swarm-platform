"""Cost tracking for Claude API usage."""

from dataclasses import dataclass, field
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelPricing:
    """Pricing information for a Claude model."""

    input_cost_per_million: float  # Cost per million input tokens
    output_cost_per_million: float  # Cost per million output tokens


# Pricing as of January 2025 (update as needed)
MODEL_PRICING = {
    "claude-opus-4-5-20251101": ModelPricing(
        input_cost_per_million=15.0,
        output_cost_per_million=75.0,
    ),
    "claude-sonnet-4-5-20250929": ModelPricing(
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
    ),
    "claude-3-5-sonnet-20241022": ModelPricing(
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
    ),
    "claude-3-5-haiku-20241022": ModelPricing(
        input_cost_per_million=1.0,
        output_cost_per_million=5.0,
    ),
    # Default fallback pricing (use Opus as conservative estimate)
    "default": ModelPricing(
        input_cost_per_million=15.0,
        output_cost_per_million=75.0,
    ),
}


@dataclass
class CostTracker:
    """Tracks API costs across all requests."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    costs_by_model: dict[str, dict[str, float]] = field(default_factory=dict)

    def track_usage(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Track token usage and calculate cost.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD for this request
        """
        # Update total tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Get pricing for model
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_million
        total_cost = input_cost + output_cost

        # Track by model
        if model not in self.costs_by_model:
            self.costs_by_model[model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            }

        self.costs_by_model[model]["input_tokens"] += input_tokens
        self.costs_by_model[model]["output_tokens"] += output_tokens
        self.costs_by_model[model]["cost_usd"] += total_cost

        logger.debug(
            "Usage tracked",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=f"${total_cost:.6f}",
        )

        return total_cost

    def get_total_cost(self) -> float:
        """Get total cost across all models.

        Returns:
            Total cost in USD
        """
        return sum(model_data["cost_usd"] for model_data in self.costs_by_model.values())

    def get_total_tokens(self) -> int:
        """Get total tokens used.

        Returns:
            Total token count
        """
        return self.total_input_tokens + self.total_output_tokens

    def generate_report(self) -> dict[str, Any]:
        """Generate a cost report.

        Returns:
            Dictionary with cost breakdown
        """
        report = {
            "total_cost_usd": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "by_model": {},
        }

        for model, data in self.costs_by_model.items():
            report["by_model"][model] = {
                "input_tokens": data["input_tokens"],
                "output_tokens": data["output_tokens"],
                "total_tokens": data["input_tokens"] + data["output_tokens"],
                "cost_usd": data["cost_usd"],
            }

        return report

    def reset(self) -> None:
        """Reset all tracking data."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.costs_by_model.clear()
