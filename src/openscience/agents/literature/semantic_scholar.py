"""Citation network analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SemanticScholarAgent(BaseAgent):
    """Agent for citation network analysis."""

    metadata = AgentMetadata(
        name="semantic_scholar",
        category="literature",
        description="Citation network analysis",
        required_skills=["semantic_scholar_api", "network_analysis"],
        input_types=["paper_id"],
        output_types=["citation_graph"],
    )

    async def execute(self, task, context):
        """Run citation network analysis."""
        result = await self.run_skill(
            "semantic_scholar_api",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
