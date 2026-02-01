"""Configuration models for the agentic swarm platform."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnthropicConfig(BaseModel):
    """Configuration for Anthropic API."""

    api_key: str | None = Field(default=None, description="Anthropic API key (optional with claude-code backend)")
    default_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Default Claude model to use",
    )
    max_tokens: int = Field(default=4096, description="Maximum tokens per response")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    timeout: float = Field(default=300.0, description="API request timeout in seconds")


class RateLimitConfig(BaseModel):
    """Configuration for API rate limiting."""

    max_requests_per_minute: int = Field(
        default=50, description="Maximum API requests per minute"
    )
    max_tokens_per_minute: int = Field(
        default=200000, description="Maximum tokens per minute"
    )
    max_concurrent_requests: int = Field(
        default=10, description="Maximum concurrent API requests"
    )


class OrchestratorConfig(BaseModel):
    """Configuration for the orchestrator."""

    max_task_retries: int = Field(default=3, description="Maximum retries per failed task")
    task_timeout: float = Field(default=600.0, description="Task execution timeout in seconds")
    execution_loop_delay: float = Field(
        default=0.1, description="Delay between execution loop iterations"
    )
    enable_parallel_execution: bool = Field(
        default=True, description="Enable parallel task execution"
    )


class AgentPoolConfig(BaseModel):
    """Configuration for the agent pool."""

    max_agents: int = Field(default=5, ge=1, le=20, description="Maximum number of agents")
    min_agents: int = Field(default=1, ge=1, description="Minimum number of agents")
    enable_auto_scaling: bool = Field(default=False, description="Enable automatic scaling")
    agent_idle_timeout: float = Field(
        default=300.0, description="Idle timeout before agent shutdown"
    )

    # Agent distribution by type
    code_agent_count: int = Field(default=2, description="Number of code generation agents")
    docs_agent_count: int = Field(default=1, description="Number of documentation agents")
    analysis_agent_count: int = Field(default=1, description="Number of analysis agents")
    test_agent_count: int = Field(default=1, description="Number of testing agents")


class MonitoringConfig(BaseModel):
    """Configuration for monitoring and logging."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    enable_cost_tracking: bool = Field(default=True, description="Enable cost tracking")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    output_directory: Path = Field(
        default=Path("./output"), description="Directory for output files"
    )


class BackendConfig(BaseModel):
    """Configuration for execution backend."""

    type: Literal["anthropic", "interactive"] = Field(
        default="interactive",
        description="Backend type: anthropic (API with key) or interactive (manual, no key)"
    )


class SwarmConfig(BaseSettings):
    """Main configuration class for the agentic swarm platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="allow",  # Allow extra fields for optional API key
    )

    # API Configuration (optional now)
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    # Sub-configurations
    backend: BackendConfig = Field(default_factory=BackendConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    agent_pool: AgentPoolConfig = Field(default_factory=AgentPoolConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    def model_post_init(self, __context: object) -> None:
        """Post-initialization to set API key in anthropic config."""
        # Only require API key if using anthropic backend
        if self.backend.type == "anthropic":
            if not self.anthropic_api_key:
                from src.utils.errors import ConfigurationError
                raise ConfigurationError(
                    "ANTHROPIC_API_KEY is required when using 'anthropic' backend. "
                    "Use --backend interactive or --backend claude-code to run without API key."
                )
        if self.anthropic_api_key:
            self.anthropic.api_key = self.anthropic_api_key


def load_config(config_path: Path | None = None) -> SwarmConfig:
    """Load configuration from file and environment variables.

    Args:
        config_path: Optional path to YAML config file

    Returns:
        Loaded configuration
    """
    import yaml
    from src.utils.errors import ConfigurationError

    config_dict = {}

    # Load from YAML file if provided
    if config_path and config_path.exists():
        try:
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {config_path}: {e}")

    # Environment variables take precedence
    try:
        config = SwarmConfig(**config_dict)
    except Exception as e:
        raise ConfigurationError(f"Invalid configuration: {e}")

    return config
