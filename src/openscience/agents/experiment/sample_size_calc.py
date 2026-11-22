"""Sample size determination agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SampleSizeCalcAgent(BaseAgent):
    """Agent for sample size determination."""

    metadata = AgentMetadata(
        name="sample_size_calc",
        category="experiment",
        description="Sample size determination",
        required_skills=["statsmodels", "power_analysis"],
        input_types=["parameters"],
        output_types=["sample_size"],
    )

    async def execute(self, task, context):
        """Run sample size determination."""
        result = await self.run_skill(
            "statsmodels",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
