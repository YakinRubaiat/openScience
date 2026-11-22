"""Survival analysis and Kaplan-Meier agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SurvivalAnalyzerAgent(BaseAgent):
    """Agent for survival analysis and Kaplan-Meier."""

    metadata = AgentMetadata(
        name="survival_analyzer",
        category="analysis",
        description="Survival analysis and Kaplan-Meier",
        required_skills=["lifelines", "survival_analysis"],
        input_types=["survival_data"],
        output_types=["km_curves"],
    )

    async def execute(self, task, context):
        """Run survival analysis and Kaplan-Meier."""
        result = await self.run_skill(
            "lifelines",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
