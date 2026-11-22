"""Reagent selection and concentration agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ReagentOptimizerAgent(BaseAgent):
    """Agent for reagent selection and concentration."""

    metadata = AgentMetadata(
        name="reagent_optimizer",
        category="experiment",
        description="Reagent selection and concentration",
        required_skills=["optimization_algorithms", "reagent_database"],
        input_types=["reaction_conditions"],
        output_types=["optimal_reagents"],
    )

    async def execute(self, task, context):
        """Run reagent selection and concentration."""
        result = await self.run_skill(
            "optimization_algorithms",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
