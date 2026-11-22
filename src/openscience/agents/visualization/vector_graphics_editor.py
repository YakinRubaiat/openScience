"""SVG/PDF optimization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class VectorGraphicsEditorAgent(BaseAgent):
    """Agent for sVG/PDF optimization."""

    metadata = AgentMetadata(
        name="vector_graphics_editor",
        category="visualization",
        description="SVG/PDF optimization",
        required_skills=["cairosvg", "vector_editing"],
        input_types=["svg_file"],
        output_types=["optimized_svg"],
    )

    async def execute(self, task, context):
        """Run sVG/PDF optimization."""
        result = await self.run_skill(
            "cairosvg",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
