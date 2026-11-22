"""Citation network visualization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class CitationGraphAgent(BaseAgent):
    """Agent for citation network visualization."""

    metadata = AgentMetadata(
        name="citation_graph",
        category="literature",
        description="Citation network visualization",
        required_skills=["networkx", "graph_visualization"],
        input_types=["citation_data"],
        output_types=["network_graph"],
    )

    async def execute(self, task, context):
        """Run citation network visualization."""
        result = await self.run_skill(
            "networkx",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
