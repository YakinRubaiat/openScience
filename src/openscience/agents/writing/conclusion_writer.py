"""Conclusion and future directions agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class ConclusionWriterAgent(BaseAgent):
    """Agent for conclusion and future directions."""

    metadata = AgentMetadata(
        name="conclusion_writer",
        category="writing",
        description="Conclusion and future directions",
        required_skills=["conclusion_writing", "future_work_synthesis"],
        input_types=["study_summary"],
        output_types=["conclusion"],
    )

    async def execute(self, task, context):
        """Run conclusion and future directions."""
        result = await self.run_skill(
            "conclusion_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
