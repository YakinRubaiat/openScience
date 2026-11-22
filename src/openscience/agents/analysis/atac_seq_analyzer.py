"""ATAC-seq analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class AtacSeqAnalyzerAgent(BaseAgent):
    """Agent for aTAC-seq analysis."""

    metadata = AgentMetadata(
        name="atac_seq_analyzer",
        category="analysis",
        description="ATAC-seq analysis",
        required_skills=["macs2", "chromVAR"],
        input_types=["atac_bam"],
        output_types=["accessibility_results"],
    )

    async def execute(self, task, context):
        """Run aTAC-seq analysis."""
        result = await self.run_skill(
            "macs2",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
