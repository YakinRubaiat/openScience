"""Budget and cost projection agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class CostEstimatorAgent(BaseAgent):
    """Agent for budget and cost projection."""

    metadata = AgentMetadata(
        name="cost_estimator",
        category="experiment",
        description="Budget and cost projection",
        required_skills=["cost_modeling", "budget_optimization"],
        input_types=["resource_requirements"],
        output_types=["cost_breakdown"],
    )

    async def execute(self, task, context):
        """Run budget and cost projection."""
        result = await self.run_skill(
            "cost_modeling",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
