"""Randomization and blinding schemes agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class RandomizationPlannerAgent(BaseAgent):
    """Agent for randomization and blinding schemes."""

    metadata = AgentMetadata(
        name="randomization_planner",
        category="experiment",
        description="Randomization and blinding schemes",
        required_skills=["randomization_algorithms", "blinding_protocols"],
        input_types=["study_design"],
        output_types=["randomization_plan"],
    )

    async def execute(self, task, context):
        """Run randomization and blinding schemes."""
        result = await self.run_skill(
            "randomization_algorithms",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
