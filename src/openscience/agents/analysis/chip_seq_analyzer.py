"""ChIP-seq peak calling and analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ChipSeqAnalyzerAgent(BaseAgent):
    """Agent for chIP-seq peak calling and analysis."""

    metadata = AgentMetadata(
        name="chip_seq_analyzer",
        category="analysis",
        description="ChIP-seq peak calling and analysis",
        required_skills=["macs2", "homer"],
        input_types=["chip_bam"],
        output_types=["peak_calls"],
    )

    async def execute(self, task, context):
        """Run chIP-seq peak calling and analysis."""
        result = await self.run_skill(
            "macs2",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
