"""Positive/negative control selection agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ControlDesignerAgent(BaseAgent):
    """Agent for positive/negative control selection."""

    metadata = AgentMetadata(
        name="control_designer",
        category="experiment",
        description="Positive/negative control selection",
        required_skills=["control_theory", "experimental_design"],
        input_types=["experiment_parameters"],
        output_types=["control_plan"],
    )

    async def execute(self, task, context):
        """Run positive/negative control selection."""
        result = await self.run_skill(
            "control_theory",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
