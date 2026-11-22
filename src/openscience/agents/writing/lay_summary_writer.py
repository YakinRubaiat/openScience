"""Plain language summary agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class LaySummaryWriterAgent(BaseAgent):
    """Agent for plain language summary."""

    metadata = AgentMetadata(
        name="lay_summary_writer",
        category="writing",
        description="Plain language summary",
        required_skills=["science_communication", "plain_language"],
        input_types=["technical_content"],
        output_types=["lay_summary"],
    )

    async def execute(self, task, context):
        """Run plain language summary."""
        result = await self.run_skill(
            "science_communication",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
