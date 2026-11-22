"""Dose-response curve optimization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DoseResponseDesignAgent(BaseAgent):
    """Agent for dose-response curve optimization."""

    metadata = AgentMetadata(
        name="dose_response_design",
        category="experiment",
        description="Dose-response curve optimization",
        required_skills=["dose_response_analysis", "curve_fitting"],
        input_types=["dose_range"],
        output_types=["optimal_doses"],
    )

    async def execute(self, task, context):
        """Run dose-response curve optimization."""
        result = await self.run_skill(
            "dose_response_analysis",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
