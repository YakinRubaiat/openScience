"""Cover letter drafting agent."""

from openscience.core.agent import AgentMetadata, BaseAgent


class CoverLetterWriterAgent(BaseAgent):
    """Agent for cover letter drafting."""

    metadata = AgentMetadata(
        name="cover_letter_writer",
        category="writing",
        description="Cover letter drafting",
        required_skills=["letter_writing", "submission_guidelines"],
        input_types=["manuscript_summary"],
        output_types=["cover_letter"],
    )

    async def execute(self, task, context):
        """Run cover letter drafting."""
        result = await self.run_skill(
            "letter_writing",
            operation="run",
            parameters=task.parameters,
            context=context,
        )

        return self.format_result(result)
