"""Single-cell analysis (Seurat) agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SeuratSpecialistAgent(BaseAgent):
    """Agent for single-cell analysis (Seurat)."""

    metadata = AgentMetadata(
        name="seurat_specialist",
        category="analysis",
        description="Single-cell analysis (Seurat)",
        required_skills=["seurat", "rpy2"],
        input_types=["seurat_object"],
        output_types=["analysis_results"],
    )

    async def execute(self, task, context):
        """Run single-cell analysis (Seurat)."""
        result = await self.run_skill(
            "seurat",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
