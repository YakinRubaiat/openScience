"""Single-cell analysis (Scanpy) agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ScanpySpecialistAgent(BaseAgent):
    """Agent for single-cell analysis (Scanpy)."""

    metadata = AgentMetadata(
        name="scanpy_specialist",
        category="analysis",
        description="Single-cell analysis (Scanpy)",
        required_skills=["scanpy", "anndata"],
        input_types=["h5ad_file"],
        output_types=["analysis_results"],
    )

    async def execute(self, task, context):
        """Run single-cell analysis (Scanpy)."""
        result = await self.run_skill(
            "scanpy",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
