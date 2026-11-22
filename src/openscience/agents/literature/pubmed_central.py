"""Full-text article mining agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PubmedCentralAgent(BaseAgent):
    """Agent for full-text article mining."""

    metadata = AgentMetadata(
        name="pubmed_central",
        category="literature",
        description="Full-text article mining",
        required_skills=["pmc_api", "fulltext_parser"],
        input_types=["query"],
        output_types=["fulltext_data"],
    )

    async def execute(self, task, context):
        """Run full-text article mining."""
        result = await self.run_skill(
            "pmc_api",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
