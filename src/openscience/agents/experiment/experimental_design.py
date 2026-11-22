"""Factorial and response surface designs agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ExperimentalDesignAgent(BaseAgent):
    """Agent for factorial and response surface designs."""

    metadata = AgentMetadata(
        name="experimental_design",
        category="experiment",
        description="Factorial and response surface designs",
        required_skills=["pyDOE2", "design_of_experiments"],
        input_types=["factors"],
        output_types=["design_matrix"],
    )

    async def execute(self, task, context):
        """Run factorial and response surface designs."""
        result = await self.run_skill(
            "pyDOE2",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
