"""Emerging topic detection agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class TrendTrackerAgent(BaseAgent):
    """Agent for emerging topic detection."""

    metadata = AgentMetadata(
        name="trend_tracker",
        category="literature",
        description="Emerging topic detection",
        required_skills=["topic_modeling", "trend_detection"],
        input_types=["time_series_papers"],
        output_types=["trend_report"],
    )

    async def execute(self, task, context):
        """Run emerging topic detection."""
        result = await self.run_skill(
            "topic_modeling",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
