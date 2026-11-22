"""Metabolomics data analysis agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MetabolomicsAnalyzerAgent(BaseAgent):
    """Agent for metabolomics data analysis."""

    metadata = AgentMetadata(
        name="metabolomics_analyzer",
        category="analysis",
        description="Metabolomics data analysis",
        required_skills=["xcms", "metabolomics_tools"],
        input_types=["mzml_files"],
        output_types=["metabolite_data"],
    )

    async def execute(self, task, context):
        """Run metabolomics data analysis."""
        result = await self.run_skill(
            "xcms",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
