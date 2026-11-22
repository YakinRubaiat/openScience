"""Multi-omics data integration agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class DataIntegratorAgent(BaseAgent):
    """Agent for multi-omics data integration."""

    metadata = AgentMetadata(
        name="data_integrator",
        category="data_management",
        description="Multi-omics data integration",
        required_skills=["multiomics_integration", "data_alignment"],
        input_types=["omics_datasets"],
        output_types=["integrated_data"],
    )

    async def execute(self, task, context):
        """Run multi-omics data integration."""
        result = await self.run_skill(
            "multiomics_integration",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
