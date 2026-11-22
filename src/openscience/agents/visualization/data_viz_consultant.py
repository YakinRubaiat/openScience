"""Visualization best practices agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DataVizConsultantAgent(BaseAgent):
    """Agent for visualization best practices."""

    metadata = AgentMetadata(
        name="data_viz_consultant",
        category="visualization",
        description="Visualization best practices",
        required_skills=["viz_guidelines", "chart_selection"],
        input_types=["data_type"],
        output_types=["viz_recommendations"],
    )

    async def execute(self, task, context):
        """Run visualization best practices."""
        result = await self.run_skill(
            "viz_guidelines",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
