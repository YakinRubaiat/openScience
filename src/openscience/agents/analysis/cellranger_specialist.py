"""10x Genomics preprocessing agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class CellrangerSpecialistAgent(BaseAgent):
    """Agent for 10x Genomics preprocessing."""

    metadata = AgentMetadata(
        name="cellranger_specialist",
        category="analysis",
        description="10x Genomics preprocessing",
        required_skills=["cellranger", "fastq_processing"],
        input_types=["fastq_files"],
        output_types=["count_matrix"],
    )

    async def execute(self, task, context):
        """Run 10x Genomics preprocessing."""
        result = await self.run_skill(
            "cellranger",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
