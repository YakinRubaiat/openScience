"""Statistical power calculation agent for experiment planning."""

from openscience.core.agent import BaseAgent, AgentMetadata


class PowerAnalysisAgent(BaseAgent):
    """Agent for calculating statistical power and sample sizes."""

    metadata = AgentMetadata(
        name="power_analysis",
        category="experiment",
        description="Statistical power calculation",
        required_skills=["statsmodels", "numpy_stats"],
        input_types=["effect_size", "alpha", "power_target"],
        output_types=["sample_size", "power_curve"],
    )

    async def execute(self, task, context):
        """Calculate required sample size for desired power."""
        effect_size = task.parameters.get("effect_size", 0.5)
        alpha = task.parameters.get("alpha", 0.05)
        power = task.parameters.get("power", 0.8)

        result = await self.run_skill(
            "statsmodels",
            operation="power_analysis",
            effect_size=effect_size,
            alpha=alpha,
            power=power,
        )

        return self.format_result(result)
