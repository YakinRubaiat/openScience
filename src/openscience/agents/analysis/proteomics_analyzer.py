"""Mass spec proteomics agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ProteomicsAnalyzerAgent(BaseAgent):
    """Agent for mass spec proteomics."""

    metadata = AgentMetadata(
        name="proteomics_analyzer",
        category="analysis",
        description="Mass spec proteomics",
        required_skills=["maxquant", "proteomics_tools"],
        input_types=["raw_files"],
        output_types=["protein_quant"],
    )

    async def execute(self, task, context):
        """Run mass spec proteomics."""
        result = await self.run_skill(
            "maxquant",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
