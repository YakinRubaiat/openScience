"""Storage optimization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class CompressionOptimizerAgent(BaseAgent):
    """Agent for storage optimization."""

    metadata = AgentMetadata(
        name="compression_optimizer",
        category="data_management",
        description="Storage optimization",
        required_skills=["compression_algorithms", "storage_optimization"],
        input_types=["data"],
        output_types=["compressed_data"],
    )

    async def execute(self, task, context):
        """Run storage optimization."""
        result = await self.run_skill(
            "compression_algorithms",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
