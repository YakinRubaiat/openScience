"""Meta-analysis and forest plots agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MetaAnalysisAgent(BaseAgent):
    """Agent for meta-analysis and forest plots."""

    metadata = AgentMetadata(
        name="meta_analysis",
        category="literature",
        description="Meta-analysis and forest plots",
        required_skills=["statsmodels_meta", "forest_plot"],
        input_types=["effect_sizes"],
        output_types=["meta_analysis_results"],
    )

    async def execute(self, task, context):
        """Run meta-analysis and forest plots."""
        result = await self.run_skill(
            "statsmodels_meta",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
