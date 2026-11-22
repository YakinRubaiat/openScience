"""Web-based dashboard creation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class InteractiveDashboardAgent(BaseAgent):
    """Agent for web-based dashboard creation."""

    metadata = AgentMetadata(
        name="interactive_dashboard",
        category="visualization",
        description="Web-based dashboard creation",
        required_skills=["dash", "plotly_dash"],
        input_types=["data"],
        output_types=["dashboard_app"],
    )

    async def execute(self, task, context):
        """Run web-based dashboard creation."""
        result = await self.run_skill(
            "dash",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
