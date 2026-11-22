"""Matplotlib figure optimization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MatplotlibStylistAgent(BaseAgent):
    """Agent for optimizing matplotlib figures for publication."""

    metadata = AgentMetadata(
        name="matplotlib_stylist",
        category="visualization",
        description="Matplotlib figure optimization",
        required_skills=["matplotlib", "style_sheets"],
        input_types=["figure", "style_preference"],
        output_types=["optimized_figure", "style_guide"],
    )

    async def execute(self, task, context):
        """Optimize matplotlib figure for publication."""
        figure = task.parameters.get("figure")
        style = task.parameters.get("style", "nature")

        optimized = await self.run_skill(
            "matplotlib",
            operation="apply_style",
            figure=figure,
            style=style,
        )

        return self.format_result({"figure": optimized, "style": style})
