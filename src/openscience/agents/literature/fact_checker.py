"""Claim verification against sources agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class FactCheckerAgent(BaseAgent):
    """Agent for claim verification against sources."""

    metadata = AgentMetadata(
        name="fact_checker",
        category="literature",
        description="Claim verification against sources",
        required_skills=["crossref_api", "fact_verification"],
        input_types=["claims"],
        output_types=["verification_report"],
    )

    async def execute(self, task, context):
        """Run claim verification against sources."""
        result = await self.run_skill(
            "crossref_api",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
