"""Network and graph visualization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class GraphNetworkVisualizerAgent(BaseAgent):
    """Agent for network and graph visualization."""

    metadata = AgentMetadata(
        name="graph_network_visualizer",
        category="visualization",
        description="Network and graph visualization",
        required_skills=["networkx", "graphviz"],
        input_types=["network_data"],
        output_types=["network_graph"],
    )

    async def execute(self, task, context):
        """Run network and graph visualization."""
        result = await self.run_skill(
            "networkx",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
