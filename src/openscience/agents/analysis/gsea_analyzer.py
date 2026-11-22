"""Gene set enrichment analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class GseaAnalyzerAgent(BaseAgent):
    """Agent for gene set enrichment analysis."""

    metadata = AgentMetadata(
        name="gsea_analyzer",
        category="analysis",
        description="Gene set enrichment analysis",
        required_skills=["gseapy", "msigdb"],
        input_types=["gene_list"],
        output_types=["enrichment_results"],
    )

    async def execute(self, task, context):
        """Run gene set enrichment analysis."""
        result = await self.run_skill(
            "gseapy",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
