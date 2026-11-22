"""Interactive visualizations agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PlotlySpecialistAgent(BaseAgent):
    """Agent for interactive visualizations."""

    metadata = AgentMetadata(
        name="plotly_specialist",
        category="visualization",
        description="Interactive visualizations",
        required_skills=["plotly", "interactive_viz"],
        input_types=["data"],
        output_types=["interactive_plot"],
    )

    async def execute(self, task, context):
        """Run interactive visualizations."""
        result = await self.run_skill(
            "plotly",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
