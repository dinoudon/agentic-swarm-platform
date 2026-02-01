"""CLI entry point for the agentic swarm platform."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

from src.core.orchestrator import Orchestrator
from src.models.config import SwarmConfig, load_config
from src.utils.logger import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


@click.group()
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--log-level", type=str, default="INFO", help="Logging level")
@click.pass_context
def cli(ctx: click.Context, config: str | None, log_level: str) -> None:
    """Agentic Swarm Platform - Multi-agent PRD execution system."""
    # Setup logging
    setup_logging(log_level)

    # Load configuration
    config_path = Path(config) if config else Path("config/default.yaml")
    ctx.obj = load_config(config_path if config_path.exists() else None)


@cli.command()
@click.argument("prd_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="./output", help="Output directory")
@click.option("--max-agents", type=int, help="Override maximum number of agents")
@click.option("--dry-run", is_flag=True, help="Parse only, don't execute")
@click.option(
    "--backend",
    type=click.Choice(["anthropic", "interactive"], case_sensitive=False),
    default=None,
    help="Execution backend (anthropic=API with key, interactive=manual no key)",
)
@click.pass_obj
def run(
    config: SwarmConfig,
    prd_file: str,
    output: str,
    max_agents: int | None,
    dry_run: bool,
    backend: str | None,
) -> None:
    """Execute a PRD file with the agent swarm."""
    prd_path = Path(prd_file)
    output_path = Path(output)

    # Override config if needed
    if max_agents:
        config.agent_pool.max_agents = max_agents

    if backend:
        config.backend.type = backend  # type: ignore

    # Update output directory
    config.monitoring.output_directory = output_path

    # Show backend info
    backend_display = config.backend.type.upper()
    if config.backend.type == "interactive":
        backend_display += " (NO API KEY NEEDED)"

    console.print(Panel.fit(
        f"[bold cyan]Agentic Swarm Platform[/bold cyan]\n"
        f"PRD: {prd_path.name}\n"
        f"Backend: {backend_display}\n"
        f"Output: {output_path}",
        border_style="cyan"
    ))

    if dry_run:
        asyncio.run(_run_dry_run(config, prd_path))
    else:
        asyncio.run(_run_full_execution(config, prd_path, output_path))


async def _run_dry_run(config: SwarmConfig, prd_path: Path) -> None:
    """Run analysis without execution."""
    from src.core.prd_parser import PRDParser
    from src.services.claude_client import ClaudeClient

    console.print("\n[yellow]Running in DRY RUN mode (no execution)[/yellow]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Parse PRD
        task = progress.add_task("Parsing PRD...", total=None)
        claude_client = ClaudeClient(config.anthropic)
        parser = PRDParser(claude_client)
        prd = await parser.parse_file(prd_path)
        progress.update(task, description=f"✓ Parsed PRD: {prd.metadata.title}")

        # Slice into tasks
        task = progress.add_task("Analyzing and slicing into tasks...", total=None)
        task_graph = await parser.slice_into_tasks(prd)
        progress.update(task, description=f"✓ Created {len(task_graph.tasks)} tasks")

    # Display task breakdown
    _display_task_breakdown(task_graph)


async def _run_full_execution(config: SwarmConfig, prd_path: Path, output_path: Path) -> None:
    """Run full execution with agents."""
    orchestrator = Orchestrator(config)

    # Setup progress tracking
    progress_data = {"completed": 0, "failed": 0, "total": 0}

    async def on_progress(data: dict[str, Any]) -> None:
        progress_data.update(data)

    orchestrator.event_bus.subscribe("progress.update", on_progress)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            exec_task = progress.add_task("Executing PRD...", total=100)

            # Run execution in background while updating progress
            async def update_progress() -> None:
                while not progress.finished:
                    if progress_data["total"] > 0:
                        pct = (progress_data["completed"] + progress_data["failed"]) / progress_data["total"] * 100
                        progress.update(
                            exec_task,
                            completed=pct,
                            description=f"Executing tasks ({progress_data['completed']}/{progress_data['total']} completed)",
                        )
                    await asyncio.sleep(0.5)

            # Run both tasks
            update_task = asyncio.create_task(update_progress())
            result = await orchestrator.execute_prd_file(prd_path)
            update_task.cancel()

            progress.update(exec_task, completed=100, description="✓ Execution complete")

        # Display results
        _display_results(result)

        # Save results to disk
        await _save_results(result, output_path)

        console.print(f"\n[green]✓ Results saved to {output_path}[/green]")

    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        logger.exception("Execution failed")
        sys.exit(1)


def _display_task_breakdown(task_graph: Any) -> None:
    """Display task breakdown table."""
    table = Table(title="Task Breakdown", show_header=True, header_style="bold cyan")
    table.add_column("Type", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Priority", style="yellow")
    table.add_column("Complexity", style="magenta")
    table.add_column("Dependencies", style="dim")

    for task in task_graph.tasks.values():
        deps = str(len(task.depends_on)) if task.depends_on else "-"
        table.add_row(
            task.type.value,
            task.title[:50],
            task.priority.value,
            task.complexity.value,
            deps,
        )

    console.print("\n")
    console.print(table)

    stats = task_graph.get_stats()
    console.print(f"\n[bold]Total Tasks:[/bold] {stats['total']}")
    console.print("[bold]By Type:[/bold]")
    for task_type, count in stats["by_type"].items():
        console.print(f"  - {task_type}: {count}")


def _display_results(result: Any) -> None:
    """Display execution results."""
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Execution Results[/bold cyan]")
    console.print("=" * 60)

    # Summary stats
    stats = result.generate_summary_stats()
    console.print(f"\n[bold]Status:[/bold] {result.status.value.upper()}")
    console.print(f"[bold]Success Rate:[/bold] {stats['success_rate']}")
    console.print(f"[bold]Duration:[/bold] {stats['total_duration']}")
    console.print(f"[bold]Total Tokens:[/bold] {stats['total_tokens']:,}")
    console.print(f"[bold]Estimated Cost:[/bold] {stats['estimated_cost']}")
    console.print(f"[bold]Artifacts Generated:[/bold] {stats['artifacts_generated']}")

    # Artifacts by type
    if result.artifacts_by_type:
        console.print("\n[bold]Artifacts by Type:[/bold]")
        for artifact_type, artifacts in result.artifacts_by_type.items():
            console.print(f"  - {artifact_type}: {len(artifacts)} items")

    # Executive summary
    if result.executive_summary:
        console.print("\n[bold]Executive Summary:[/bold]")
        console.print(Panel(result.executive_summary, border_style="blue"))


async def _save_results(result: Any, output_path: Path) -> None:
    """Save results to output directory."""
    import aiofiles

    output_path.mkdir(parents=True, exist_ok=True)

    # Save summary
    summary_path = output_path / "summary.md"
    async with aiofiles.open(summary_path, "w") as f:
        await f.write(f"# Execution Summary\n\n")
        await f.write(f"**PRD:** {result.prd_title}\n\n")
        await f.write(f"**Status:** {result.status.value}\n\n")
        await f.write(f"**Success Rate:** {result.get_success_rate():.1f}%\n\n")
        await f.write(f"**Duration:** {result.total_duration_seconds:.2f}s\n\n")
        await f.write(f"**Total Tokens:** {result.total_tokens:,}\n\n")
        await f.write(f"**Estimated Cost:** ${result.estimated_cost_usd:.4f}\n\n")

        if result.executive_summary:
            await f.write(f"## Executive Summary\n\n{result.executive_summary}\n\n")

        await f.write(f"## Artifacts\n\n")
        for artifact_type, artifacts in result.artifacts_by_type.items():
            await f.write(f"- {artifact_type}: {len(artifacts)} items\n")

    # Save artifacts by type
    for artifact_type, artifacts in result.artifacts_by_type.items():
        type_dir = output_path / artifact_type
        type_dir.mkdir(exist_ok=True)

        for artifact in artifacts:
            file_path = type_dir / (artifact.file_path or f"artifact_{artifact.name}.txt")
            async with aiofiles.open(file_path, "w") as f:
                await f.write(artifact.content)

    # Save metrics as JSON
    metrics_path = output_path / "metrics.json"
    metrics = {
        "status": result.status.value,
        "total_tasks": result.total_tasks,
        "successful_tasks": result.successful_tasks,
        "failed_tasks": result.failed_tasks,
        "total_tokens": result.total_tokens,
        "estimated_cost_usd": result.estimated_cost_usd,
        "duration_seconds": result.total_duration_seconds,
    }
    async with aiofiles.open(metrics_path, "w") as f:
        await f.write(json.dumps(metrics, indent=2))


@cli.command()
@click.argument("prd_file", type=click.Path(exists=True))
@click.pass_obj
def analyze(config: SwarmConfig, prd_file: str) -> None:
    """Analyze a PRD and show task breakdown without execution."""
    prd_path = Path(prd_file)
    asyncio.run(_run_dry_run(config, prd_path))


@cli.command()
@click.pass_obj
def config_info(config: SwarmConfig) -> None:
    """Show current configuration."""
    console.print("[bold cyan]Current Configuration[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Model", config.anthropic.default_model)
    table.add_row("Max Tokens", str(config.anthropic.max_tokens))
    table.add_row("Temperature", str(config.anthropic.temperature))
    table.add_row("Max Agents", str(config.agent_pool.max_agents))
    table.add_row("Max Concurrent Requests", str(config.rate_limit.max_concurrent_requests))
    table.add_row("Log Level", config.monitoring.log_level)
    table.add_row("Output Directory", str(config.monitoring.output_directory))

    console.print(table)


if __name__ == "__main__":
    cli()
