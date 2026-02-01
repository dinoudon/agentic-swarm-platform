"""Result aggregator for combining task results."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any

from src.models.prd import PRD
from src.models.result import AggregatedResult, Artifact, ArtifactType, ResultStatus, TaskResult
from src.services.claude_client import ClaudeClient
from src.services.cost_tracker import CostTracker
from src.utils.logger import get_logger

logger = get_logger(__name__)


SUMMARY_SYSTEM_PROMPT = """You are an expert technical writer creating executive summaries.
Your task is to create a concise, high-level summary of the work completed by a team of AI agents.

The summary should:
1. Highlight key accomplishments
2. Mention major deliverables (code, docs, tests, analysis)
3. Note any issues or failures
4. Be concise (3-5 paragraphs max)
5. Be written for a technical audience

Focus on WHAT was accomplished and WHY it matters, not HOW it was done."""


class ResultAggregator:
    """Aggregates results from multiple task executions."""

    def __init__(self, claude_client: ClaudeClient, cost_tracker: CostTracker):
        """Initialize result aggregator.

        Args:
            claude_client: Claude client for generating summaries
            cost_tracker: Cost tracker for pricing info
        """
        self.claude_client = claude_client
        self.cost_tracker = cost_tracker

    async def aggregate(
        self, task_results: list[TaskResult], prd: PRD, started_at: datetime, completed_at: datetime
    ) -> AggregatedResult:
        """Aggregate results from all tasks.

        Args:
            task_results: List of task results
            prd: Source PRD
            started_at: Execution start time
            completed_at: Execution completion time

        Returns:
            Aggregated result
        """
        logger.info("Aggregating results", result_count=len(task_results))

        # Calculate overall status
        successful = sum(1 for r in task_results if r.status == ResultStatus.SUCCESS)
        failed = sum(1 for r in task_results if r.status == ResultStatus.FAILED)
        total = len(task_results)

        if failed == 0:
            overall_status = ResultStatus.SUCCESS
        elif successful > 0:
            overall_status = ResultStatus.PARTIAL
        else:
            overall_status = ResultStatus.FAILED

        # Group artifacts by type
        artifacts_by_type: dict[str, list[Artifact]] = defaultdict(list)
        for result in task_results:
            for artifact in result.artifacts:
                artifacts_by_type[artifact.type.value].append(artifact)

        # Calculate totals
        total_input_tokens = sum(r.input_tokens for r in task_results)
        total_output_tokens = sum(r.output_tokens for r in task_results)
        total_tokens = total_input_tokens + total_output_tokens

        # Get cost from tracker
        estimated_cost = self.cost_tracker.get_total_cost()

        # Calculate duration
        duration = (completed_at - started_at).total_seconds()

        # Generate executive summary
        executive_summary = await self._generate_summary(task_results, prd, artifacts_by_type)

        # Build aggregated result
        aggregated = AggregatedResult(
            status=overall_status,
            total_tasks=total,
            successful_tasks=successful,
            failed_tasks=failed,
            task_results=task_results,
            artifacts_by_type=dict(artifacts_by_type),
            started_at=started_at,
            completed_at=completed_at,
            total_duration_seconds=duration,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            executive_summary=executive_summary,
            prd_title=prd.metadata.title,
        )

        logger.info(
            "Results aggregated",
            status=overall_status.value,
            successful=successful,
            failed=failed,
            artifacts=sum(len(arts) for arts in artifacts_by_type.values()),
        )

        return aggregated

    async def _generate_summary(
        self,
        task_results: list[TaskResult],
        prd: PRD,
        artifacts_by_type: dict[str, list[Artifact]],
    ) -> str:
        """Generate executive summary using Claude.

        Args:
            task_results: List of task results
            prd: Source PRD
            artifacts_by_type: Artifacts grouped by type

        Returns:
            Executive summary text
        """
        # Build summary of work done
        work_summary_parts = [
            f"PRD: {prd.metadata.title}",
            f"Total Tasks: {len(task_results)}",
            f"Successful: {sum(1 for r in task_results if r.status == ResultStatus.SUCCESS)}",
            f"Failed: {sum(1 for r in task_results if r.status == ResultStatus.FAILED)}",
            "",
            "Artifacts Generated:",
        ]

        for artifact_type, artifacts in artifacts_by_type.items():
            work_summary_parts.append(f"- {artifact_type}: {len(artifacts)} items")

        work_summary_parts.append("")
        work_summary_parts.append("Task Details:")
        for result in task_results:
            status_icon = "✓" if result.status == ResultStatus.SUCCESS else "✗"
            work_summary_parts.append(f"{status_icon} [{result.agent_type}] Task {result.task_id}")
            if result.error_message:
                work_summary_parts.append(f"  Error: {result.error_message}")

        work_summary = "\n".join(work_summary_parts)

        # Ask Claude to generate summary
        user_prompt = f"""Create an executive summary for the following AI agent execution:

{work_summary}

Original PRD Summary:
{prd.get_summary()}

Provide a concise executive summary highlighting what was accomplished."""

        try:
            summary, _ = await self.claude_client.create_message(
                system=SUMMARY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.7,
                max_tokens=1000,
            )
            return summary.strip()
        except Exception as e:
            logger.warning("Failed to generate executive summary", error=str(e))
            # Fallback to simple summary
            return f"Completed {len(task_results)} tasks for PRD: {prd.metadata.title}"
