"""Batch effect correction agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class BatchCorrectorAgent(BaseAgent):
    """Agent for batch effect correction."""

    metadata = AgentMetadata(
        name="batch_corrector",
        category="data_management",
        description="Batch effect correction",
        required_skills=["harmony", "combat"],
        input_types=["batched_data"],
        output_types=["corrected_data"],
    )

    async def execute(self, task, context):
        """Run batch effect correction."""
        result = await self.run_skill(
            "harmony",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
