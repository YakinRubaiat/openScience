"""Bioimage analysis (CellProfiler, Fiji) agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ImageAnalyzerAgent(BaseAgent):
    """Agent for bioimage analysis (CellProfiler, Fiji)."""

    metadata = AgentMetadata(
        name="image_analyzer",
        category="analysis",
        description="Bioimage analysis (CellProfiler, Fiji)",
        required_skills=["cellprofiler", "fiji"],
        input_types=["images"],
        output_types=["measurements"],
    )

    async def execute(self, task, context):
        """Run bioimage analysis (CellProfiler, Fiji)."""
        result = await self.run_skill(
            "cellprofiler",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
