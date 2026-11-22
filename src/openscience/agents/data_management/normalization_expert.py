"""Normalization method selection agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class NormalizationExpertAgent(BaseAgent):
    """Agent for normalization method selection."""

    metadata = AgentMetadata(
        name="normalization_expert",
        category="data_management",
        description="Normalization method selection",
        required_skills=["normalization_methods", "data_characteristics"],
        input_types=["raw_data"],
        output_types=["normalized_data"],
    )

    async def execute(self, task, context):
        """Run normalization method selection."""
        result = await self.run_skill(
            "normalization_methods",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
