"""Preprint tracking and notifications agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class BiorxivMonitorAgent(BaseAgent):
    """Agent for preprint tracking and notifications."""

    metadata = AgentMetadata(
        name="biorxiv_monitor",
        category="literature",
        description="Preprint tracking and notifications",
        required_skills=["biorxiv_api", "rss_parsing"],
        input_types=["search_terms"],
        output_types=["preprint_list"],
    )

    async def execute(self, task, context):
        """Run preprint tracking and notifications."""
        result = await self.run_skill(
            "biorxiv_api",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
