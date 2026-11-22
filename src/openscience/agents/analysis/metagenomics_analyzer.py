"""Microbiome analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MetagenomicsAnalyzerAgent(BaseAgent):
    """Agent for microbiome analysis."""

    metadata = AgentMetadata(
        name="metagenomics_analyzer",
        category="analysis",
        description="Microbiome analysis",
        required_skills=["qiime2", "dada2"],
        input_types=["fastq_files"],
        output_types=["microbiome_profile"],
    )

    async def execute(self, task, context):
        """Run microbiome analysis."""
        result = await self.run_skill(
            "qiime2",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
