"""Preregistration document drafting agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class PreregistrationWriterAgent(BaseAgent):
    """Agent for preregistration document drafting."""

    metadata = AgentMetadata(
        name="preregistration_writer",
        category="experiment",
        description="Preregistration document drafting",
        required_skills=["preregistration_templates", "study_design_documentation"],
        input_types=["study_plan"],
        output_types=["preregistration_doc"],
    )

    async def execute(self, task, context):
        """Run preregistration document drafting."""
        result = await self.run_skill(
            "preregistration_templates",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
