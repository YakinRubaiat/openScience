"""3D structure visualization agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ThreeDVisualizerAgent(BaseAgent):
    """Agent for 3D structure visualization."""

    metadata = AgentMetadata(
        name="3d_visualizer",
        category="visualization",
        description="3D structure visualization",
        required_skills=["py3Dmol", "nglview"],
        input_types=["pdb_structure"],
        output_types=["3d_visualization"],
    )

    async def execute(self, task, context):
        """Run 3D structure visualization."""
        result = await self.run_skill(
            "py3Dmol",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
