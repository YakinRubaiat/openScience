"""Publication-quality figure formatting agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PublicationFormatterAgent(BaseAgent):
    """Agent for formatting figures for publication."""

    metadata = AgentMetadata(
        name="publication_formatter",
        category="visualization",
        description="Publication-quality figure formatting",
        required_skills=["matplotlib", "style_sheets"],
        input_types=["figure_data", "viz_type"],
        output_types=["figure", "figure_path"],
    )

    async def execute(self, task, context):
        """Format analysis results as a publication-quality figure."""
        figure_data = task.parameters.get("figure_data")
        viz_type = task.parameters.get("viz_type", "auto")
        style = task.parameters.get("style", "publication")
        output_path = task.parameters.get("output_path")

        figure = await self.run_skill(
            "matplotlib",
            operation="render",
            figure_data=figure_data,
            viz_type=viz_type,
            style=style,
            output_path=output_path,
        )

        return self.format_result({"figure": figure, "viz_type": viz_type, "style": style})
