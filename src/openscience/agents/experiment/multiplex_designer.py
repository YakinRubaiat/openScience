"""Multiplex assay panel design agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class MultiplexDesignerAgent(BaseAgent):
    """Agent for multiplex assay panel design."""

    metadata = AgentMetadata(
        name="multiplex_designer",
        category="experiment",
        description="Multiplex assay panel design",
        required_skills=["multiplex_optimization", "assay_compatibility"],
        input_types=["target_list"],
        output_types=["multiplex_panel"],
    )

    async def execute(self, task, context):
        """Run multiplex assay panel design."""
        result = await self.run_skill(
            "multiplex_optimization",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
