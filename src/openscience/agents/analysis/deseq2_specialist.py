"""Bulk RNA-seq differential expression agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class Deseq2SpecialistAgent(BaseAgent):
    """Agent for bulk RNA-seq differential expression."""

    metadata = AgentMetadata(
        name="deseq2_specialist",
        category="analysis",
        description="Bulk RNA-seq differential expression",
        required_skills=["DESeq2", "rpy2"],
        input_types=["count_matrix"],
        output_types=["de_results"],
    )

    async def execute(self, task, context):
        """Run bulk RNA-seq differential expression."""
        result = await self.run_skill(
            "DESeq2",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
