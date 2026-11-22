"""R ggplot2 to Python conversion agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class GgplotConverterAgent(BaseAgent):
    """Agent for r ggplot2 to Python conversion."""

    metadata = AgentMetadata(
        name="ggplot_converter",
        category="visualization",
        description="R ggplot2 to Python conversion",
        required_skills=["plotnine", "ggplot_syntax"],
        input_types=["r_code"],
        output_types=["python_plot"],
    )

    async def execute(self, task, context):
        """Run r ggplot2 to Python conversion."""
        result = await self.run_skill(
            "plotnine",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
