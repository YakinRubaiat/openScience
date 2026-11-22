"""Technical risk identification agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class RiskAssessorAgent(BaseAgent):
    """Agent for technical risk identification."""

    metadata = AgentMetadata(
        name="risk_assessor",
        category="experiment",
        description="Technical risk identification",
        required_skills=["risk_analysis", "mitigation_planning"],
        input_types=["project_plan"],
        output_types=["risk_assessment"],
    )

    async def execute(self, task, context):
        """Run technical risk identification."""
        result = await self.run_skill(
            "risk_analysis",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
