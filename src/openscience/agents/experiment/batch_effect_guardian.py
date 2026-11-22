"""Batch effect detection and correction planning agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class BatchEffectGuardianAgent(BaseAgent):
    """Agent for batch effect detection and correction planning."""

    metadata = AgentMetadata(
        name="batch_effect_guardian",
        category="experiment",
        description="Batch effect detection and correction planning",
        required_skills=["combat", "batch_effect_detection"],
        input_types=["batch_metadata"],
        output_types=["correction_plan"],
    )

    async def execute(self, task, context):
        """Run batch effect detection and correction planning."""
        result = await self.run_skill(
            "combat",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
