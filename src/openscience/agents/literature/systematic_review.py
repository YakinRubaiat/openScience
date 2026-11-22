"""PRISMA-compliant review automation agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SystematicReviewAgent(BaseAgent):
    """Agent for pRISMA-compliant review automation."""

    metadata = AgentMetadata(
        name="systematic_review",
        category="literature",
        description="PRISMA-compliant review automation",
        required_skills=["prisma_workflow", "screening_automation"],
        input_types=["search_results"],
        output_types=["prisma_flow"],
    )

    async def execute(self, task, context):
        """Run pRISMA-compliant review automation."""
        result = await self.run_skill(
            "prisma_workflow",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
