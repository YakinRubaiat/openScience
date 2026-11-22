"""Pathway and network analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PathwayAnalyzerAgent(BaseAgent):
    """Agent for pathway and network analysis."""

    metadata = AgentMetadata(
        name="pathway_analyzer",
        category="analysis",
        description="Pathway and network analysis",
        required_skills=["pathway_databases", "network_analysis"],
        input_types=["gene_list"],
        output_types=["pathway_results"],
    )

    async def execute(self, task, context):
        """Run pathway and network analysis."""
        result = await self.run_skill(
            "pathway_databases",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
