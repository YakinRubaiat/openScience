"""Multi-panel figure composition agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class LayoutComposerAgent(BaseAgent):
    """Agent for multi-panel figure composition."""

    metadata = AgentMetadata(
        name="layout_composer",
        category="visualization",
        description="Multi-panel figure composition",
        required_skills=["matplotlib_gridspec", "layout_optimization"],
        input_types=["figures"],
        output_types=["composed_figure"],
    )

    async def execute(self, task, context):
        """Run multi-panel figure composition."""
        result = await self.run_skill(
            "matplotlib_gridspec",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
