"""Specific aims refinement agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class SpecificAimsOptimizerAgent(BaseAgent):
    """Agent for specific aims refinement."""

    metadata = AgentMetadata(
        name="specific_aims_optimizer",
        category="writing",
        description="Specific aims refinement",
        required_skills=["aims_optimization", "logic_modeling"],
        input_types=["research_objectives"],
        output_types=["refined_aims"],
    )

    async def execute(self, task, context):
        """Run specific aims refinement."""
        result = await self.run_skill(
            "aims_optimization",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
