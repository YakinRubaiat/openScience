"""Statistical inference and modeling agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class StatisticalModelerAgent(BaseAgent):
    """Agent for statistical inference and modeling."""

    metadata = AgentMetadata(
        name="statistical_modeler",
        category="analysis",
        description="Statistical inference and modeling",
        required_skills=["statsmodels", "bayesian_inference"],
        input_types=["data"],
        output_types=["model_results"],
    )

    async def execute(self, task, context):
        """Run statistical inference and modeling."""
        result = await self.run_skill(
            "statsmodels",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
