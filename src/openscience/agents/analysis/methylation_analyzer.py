"""DNA methylation analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MethylationAnalyzerAgent(BaseAgent):
    """Agent for dNA methylation analysis."""

    metadata = AgentMetadata(
        name="methylation_analyzer",
        category="analysis",
        description="DNA methylation analysis",
        required_skills=["minfi", "methylation_array"],
        input_types=["idat_files"],
        output_types=["methylation_data"],
    )

    async def execute(self, task, context):
        """Run dNA methylation analysis."""
        result = await self.run_skill(
            "minfi",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
