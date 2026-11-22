"""Accessible color scheme design agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ColorPaletteDesignerAgent(BaseAgent):
    """Agent for accessible color scheme design."""

    metadata = AgentMetadata(
        name="color_palette_designer",
        category="visualization",
        description="Accessible color scheme design",
        required_skills=["colorbrewer", "accessibility_checking"],
        input_types=["plot_type"],
        output_types=["color_palette"],
    )

    async def execute(self, task, context):
        """Run accessible color scheme design."""
        result = await self.run_skill(
            "colorbrewer",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
