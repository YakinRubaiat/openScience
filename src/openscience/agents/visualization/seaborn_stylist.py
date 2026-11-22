"""Statistical visualization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SeabornStylistAgent(BaseAgent):
    """Agent for statistical visualization."""

    metadata = AgentMetadata(
        name="seaborn_stylist",
        category="visualization",
        description="Statistical visualization",
        required_skills=["seaborn", "statistical_plots"],
        input_types=["data"],
        output_types=["statistical_plots"],
    )

    async def execute(self, task, context):
        """Run statistical visualization."""
        result = await self.run_skill(
            "seaborn",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
